// A2A Campaign Import — Figma Plugin
// Fetches the latest generated image from the harness and places it as an
// editable frame on the current page.

figma.showUI(__html__, { width: 340, height: 280, title: "A2A Campaign Import" });

figma.ui.onmessage = async (msg) => {
  if (msg.type === "import-image") {
    try {
      // Convert base64 to Uint8Array
      const binary = atob(msg.image_b64);
      const bytes  = new Uint8Array(binary.length);
      for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);

      // Register the image with Figma
      const image = figma.createImage(bytes);
      const { width, height } = await image.getSizeAsync();

      // Create a frame sized to the image (max 1080px wide)
      const scale  = Math.min(1, 1080 / width);
      const fw     = Math.round(width  * scale);
      const fh     = Math.round(height * scale);

      const frame  = figma.createFrame();
      frame.resize(fw, fh);
      frame.name   = msg.campaign_name || "A2A Generated";
      frame.fills  = [{ type: "IMAGE", imageHash: image.hash, scaleMode: "FILL" }];
      frame.cornerRadius = 0;

      // Place at viewport centre
      const vp = figma.viewport.center;
      frame.x  = vp.x - fw / 2;
      frame.y  = vp.y - fh / 2;

      figma.currentPage.appendChild(frame);
      figma.viewport.scrollAndZoomIntoView([frame]);
      figma.currentPage.selection = [frame];

      figma.ui.postMessage({ type: "done", name: frame.name });
    } catch (err) {
      figma.ui.postMessage({ type: "error", message: String(err) });
    }
  }

  if (msg.type === "close") {
    figma.closePlugin();
  }
};
