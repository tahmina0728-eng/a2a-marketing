from __future__ import annotations
import uuid

import structlog

from app.config import get_settings
from app.agents._utils import _generate, _genai_client

logger   = structlog.get_logger()
settings = get_settings()


def _stitch_tvc_clips(clips: list, brand: str, tagline: str) -> bytes:
    """Stitch a list of video clip bytes into one MP4 using FFmpeg concat."""
    import subprocess, tempfile
    from pathlib import Path as _PP

    if not clips:
        return b""
    if len(clips) == 1:
        return clips[0]

    with tempfile.TemporaryDirectory() as _td:
        for i, clip in enumerate(clips):
            (_PP(_td) / f"clip{i:02d}.mp4").write_bytes(clip)

        list_txt = "\n".join([f"file 'clip{i:02d}.mp4'" for i in range(len(clips))])
        (_PP(_td) / "list.txt").write_text(list_txt, encoding="utf-8")

        r = subprocess.run(
            ["ffmpeg", "-y", "-f", "concat", "-safe", "0",
             "-i", "list.txt", "-c", "copy", "stitched.mp4"],
            capture_output=True, timeout=300, cwd=_td,
        )
        if r.returncode != 0 or not (_PP(_td) / "stitched.mp4").exists():
            raise RuntimeError(r.stderr.decode(errors="ignore")[-300:])

        stitched = (_PP(_td) / "stitched.mp4").read_bytes()

    # Text overlay (title/tagline synced with voiceover) + brand logo end-card
    # Use _overlay_reel so text appears from t=1.5s and logo appears in the
    # last 2 seconds of the stitched video.
    try:
        from app.runner import _overlay_reel
        total_secs   = len(clips) * 6
        logo_start   = max(0.0, total_secs - 2.5)
        _overlaid = _overlay_reel(
            stitched, brand, tagline, "",
            text_start_sec=1.5,
            logo_start_sec=logo_start,
        )
        if len(_overlaid) > 1000:
            stitched = _overlaid
    except Exception as _oe:
        import logging
        logging.warning(f"tvc_overlay_failed: {_oe}")
    return stitched


def run_tvc(brand: str, prompt: str, duration: int = 30) -> dict:
    """
    Director agent: generates a 15s or 30s TV commercial.
      1. Gemini writes a scene-by-scene script (3 scenes for 15s, 5 for 30s)
      2. Veo generates each scene clip sequentially
      3. FFmpeg stitches all clips into one TVC
      4. Logo end-card applied via _overlay_logo_end_card
    """
    import time as _time, base64 as _b64
    from google.genai.types import GenerateVideosConfig

    n_scenes  = 3 if duration <= 15 else 5
    clip_dur  = 6   # Veo minimum is 6s; 3×6s ≈ 15s, 5×6s = 30s

    # ── Step 1: Script generation ────────────────────────────────────────────
    script_data = _generate(
        "You are a professional TVC director and scriptwriter for premium brand advertising.",
        brand, prompt,
        f'Respond ONLY with valid JSON — no markdown. '
        f'Write a {duration}-second TVC script with exactly {n_scenes} scenes '
        f'(each scene = 6 seconds). '
        f'CRITICAL RULES for visual descriptions: '
        f'(1) NO logos, brand cards, end cards, product packaging, text overlays or typography — '
        f'these are added in post-production. '
        f'(2) Every scene must show PEOPLE or ENVIRONMENTS — not static product shots or logo cards. '
        f'(3) No scene should describe "a card", "a logo", "a screen" or any graphic element. '
        f'{{"title":"short punchy campaign title","tagline":"one memorable end-line",'
        f'"scenes":[{{"scene":1,"visual":"cinematic visual description — people, setting, action, '
        f'lighting. No brand name, no text, no logos, no product packaging in the scene.",'
        f'"voiceover":"narrator line, max 8 words",'
        f'"mood":"e.g. warm and intimate"}}]}}',
    )

    scenes  = script_data.get("scenes", [])[:n_scenes]
    title   = script_data.get("title",   f"{brand} TVC")
    tagline = script_data.get("tagline", "")

    if not scenes:
        return {"agent":"tvc","brand":brand,"title":title,"scenes":[],"video_b64":"",
                "error":"Script generation failed — try again."}

    # ── Step 2: Generate each scene with Veo ─────────────────────────────────
    client    = _genai_client()
    from app.config import get_settings as _gs_veo2
    veo_model = _gs_veo2().veo_model
    clip_bytes_list: list[bytes] = []
    clips_b64: list[str]         = []

    import re as _re_tvc
    _LOGO_PATTERNS = _re_tvc.compile(
        r"\b(logo|brand card|end card|title card|product shot|packaging|"
        r"close.?up of (the )?product|brand name|typography|text overlay|"
        r"graphic|screen|card fades|logo appears)\b",
        _re_tvc.IGNORECASE,
    )

    _quota_hit = False
    for i, scene in enumerate(scenes):
        visual    = scene.get("visual",    "")
        voiceover = scene.get("voiceover", "")
        mood      = scene.get("mood",      "cinematic and premium")
        scene_num = i + 1

        # Strip any logo/card language Gemini may have sneaked into the visual
        visual = _LOGO_PATTERNS.sub("", visual).strip()

        veo_prompt = (
            f"Cinematic {clip_dur}-second TV commercial scene showing REAL PEOPLE and PLACES — "
            f"no static cards, no logos, no text. "
            f"{visual} "
            f"Mood: {mood}. Photorealistic premium advertising quality, "
            f"smooth camera motion, brand colours prominent. "
            f"AUDIO: brand-appropriate music with a warm confident voiceover "
            f"saying \"{voiceover}\"."
        )

        logger.info("tvc_scene_generating",
                    brand=brand, scene=scene_num, total=n_scenes, prompt=veo_prompt[:90])

        try:
            _page   = uuid.uuid4().hex[:10]
            out_uri = f"gs://{settings.gcs_bucket}/outputs/tvc-{_page}/scene{scene_num:02d}.mp4"

            # Retry on 429 with increasing backoff; on persistent quota exhaustion
            # stop early and return whatever clips we have so the caller gets a
            # graceful response (script + partial video) instead of a 500 error.
            _waits = [90, 180, 300]
            op = None
            for _attempt in range(4):
                try:
                    op = client.models.generate_videos(
                        model  = veo_model,
                        prompt = veo_prompt,
                        config = GenerateVideosConfig(
                            aspect_ratio      = "16:9",
                            duration_seconds  = clip_dur,
                            output_gcs_uri    = out_uri,
                            number_of_videos  = 1,
                            generate_audio    = True,
                            negative_prompt   = (
                        "text, subtitles, words, logos, watermarks, brand cards, "
                        "end cards, title cards, static shots, product packaging, "
                        "graphic design, typography, brand name text"
                    ),
                        ),
                    )
                    break
                except Exception as _ve:
                    _is_quota = "429" in str(_ve) or "RESOURCE_EXHAUSTED" in str(_ve)
                    if _is_quota and _attempt < 3:
                        _w = _waits[_attempt]
                        logger.warning("tvc_veo_rate_limited", scene=scene_num,
                                       attempt=_attempt+1, wait_s=_w)
                        _time.sleep(_w)
                    elif _is_quota:
                        # Quota still exhausted after all retries — stop gracefully
                        logger.warning("tvc_quota_exhausted_stopping", scene=scene_num)
                        _quota_hit = True
                        break
                    else:
                        raise

            if _quota_hit:
                break   # exit the scene loop, stitch what we have

            if op is None:
                logger.warning("tvc_scene_no_op", scene=scene_num)
                continue

            # Poll until done (max 8 min)
            deadline = _time.time() + 480
            while not op.done:
                if _time.time() > deadline:
                    logger.warning("tvc_scene_timeout", scene=scene_num)
                    break
                _time.sleep(20)
                op = client.operations.get(op)

            if op.result and op.result.generated_videos:
                _gcs_uri = op.result.generated_videos[0].video.uri
                from google.cloud import storage as _gcs
                _without = _gcs_uri[5:]
                _bucket, _, _blob = _without.partition("/")
                _clip = _gcs.Client().bucket(_bucket).blob(_blob).download_as_bytes()
                clip_bytes_list.append(_clip)
                clips_b64.append(_b64.b64encode(_clip).decode())
                logger.info("tvc_scene_done", scene=scene_num, kb=len(_clip)//1024)
            else:
                _rai = getattr(op.result, "rai_media_filtered_reasons", None) if op and op.result else None
                logger.warning("tvc_scene_empty", scene=scene_num, rai=_rai)

        except Exception as _se:
            logger.warning("tvc_scene_failed", scene=scene_num, error=str(_se))

    # ── Step 3: Stitch + logo end-card ───────────────────────────────────────
    video_b64 = ""
    if len(clip_bytes_list) >= 2:
        try:
            stitched = _stitch_tvc_clips(clip_bytes_list, brand, tagline or title)
            video_b64 = _b64.b64encode(stitched).decode()
            logger.info("tvc_stitched", brand=brand, scenes=len(clip_bytes_list),
                        total_kb=len(stitched)//1024)
        except Exception as _ste:
            logger.warning("tvc_stitch_failed", brand=brand, error=str(_ste))
            video_b64 = clips_b64[0] if clips_b64 else ""
    elif clip_bytes_list:
        video_b64 = clips_b64[0]

    _veo_error = (
        "Veo quota exhausted — script is ready. Wait a few minutes and try again, "
        "or the Vertex AI quota may need increasing."
    ) if _quota_hit and not clip_bytes_list else ""

    return {
        "agent":        "tvc",
        "brand":        brand,
        "title":        title,
        "tagline":      tagline,
        "duration":     duration,
        "n_scenes":     len(clip_bytes_list),
        "scenes":       scenes,
        "scene_clips":  clips_b64,
        "video_b64":    video_b64,
        "headline":     title,
        "body":         tagline,
        "error":        _veo_error,
    }
