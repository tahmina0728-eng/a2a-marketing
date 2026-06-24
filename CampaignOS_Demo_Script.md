# CampaignOS — Live Demo Script

**Project:** CampaignOS · Multi-Agent AI Campaign Platform
**Powered by:** Infosys Aster × Google Cloud × Gemini
**Estimated demo time:** 12–15 minutes

---

## PRE-DEMO CHECKLIST

- [ ] Browser open on CampaignOS — agent network screen visible
- [ ] Harness running on Cloud Run (or locally)
- [ ] Boozt brand selected as default
- [ ] BigQuery console open in a second tab (optional, for tech audience)
- [ ] GCS bucket open in a third tab (optional)
- [ ] Microphone on, screen sharing active

---

---

# SCENE 1 — OPENING

**[Agent network diagram visible on screen. Pause for 3 seconds before speaking.]**

> "Thank you. What I'm going to show you today is not a prototype.
> This is a live, production system — running on Google Cloud — that takes a raw campaign brief
> and produces a complete, publish-ready campaign package in under three minutes.
>
> We call it CampaignOS. It is a multi-agent AI platform built on Google's Agent Development Kit,
> powered by Gemini, and grounded in real brand data.
>
> Every output you see today is generated live. Nothing is pre-loaded. Nothing is scripted.
>
> Let me start with what you're looking at right now."

---

# SCENE 2 — THE AGENT NETWORK

**[Point to each agent node as you name them. Move your cursor to each one.]**

> "This is the Agent Network — seven specialist AI agents, each built for a specific creative role,
> all connected together in a live orchestration pipeline.
>
> At the top — **Logos**. The briefing intelligence. Logos reads your campaign brief, pulls brand
> knowledge, retrieves audience truths, and packages everything the other agents need to do
> their jobs.
>
> On the upper right — **Helia**. The strategy agent. Helia takes Logos's briefing package and
> builds the creative territory — the big idea the entire campaign is anchored to.
>
> Below Helia — **Ideon**. The copy agent. Ideon writes the actual words — headlines, body copy,
> scripts, CTAs — all in the brand's voice, all consistent with the strategy.
>
> Bottom right — **Aether**. Cultural intelligence. Aether analyses what is happening in the world
> right now — trends, moments, audience behaviour — and makes sure the campaign is culturally
> relevant, not just brand-correct.
>
> On the left — **Morphis**. The visual agent. Morphis generates key visual concepts and actual
> images using Gemini's image generation, guided entirely by the brief.
>
> Above Morphis — **Kinetik**. The video agent. Kinetik produces a short-form campaign reel,
> optimised for TikTok and Instagram Reels.
>
> And finally — **Poly**. The channel agent. Poly takes everything the other agents have built
> and adapts it for every platform — Instagram, TikTok, Google Ads, Email — with the right
> format, right length, and right tone for each.
>
> These seven agents don't run in a simple chain. They execute as a directed workflow graph —
> each node's output feeds the next, in parallel where possible — all orchestrated by
> Google's Agent Development Kit."

---

# SCENE 3 — SELECTING THE BRAND

**[Click the brand selector. Choose Boozt. Speak as you click.]**

> "To run a campaign, I select a brand. Today — Boozt. An energy drink brand targeting
> gym-goers, festival crowds, and gamers across the UK.
>
> The moment I select this brand, the system knows exactly where to find its knowledge.
> Boozt's brand guidelines, product information, tone of voice, forbidden terms —
> all of it — are stored in Google Cloud Storage, indexed in Vertex AI Search,
> and embedded as vectors in Cloud SQL with pgvector.
>
> I'll show you exactly what that means when the pipeline runs.
>
> Now — the brief."

---

# SCENE 4 — ENTERING THE BRIEF

**[Click into the brief input field. Type slowly so the audience can read along.]**

> "I'm going to type a very simple brief. In the real world this comes from your account team,
> your client, your planning document. Here — one paragraph is enough."

**[Type:]**
**"Summer festival campaign. Target audience: 18 to 28 year olds, UK. Product: Boozt Original Energy. Campaign goal: brand awareness and trial at live events."**

> "That's it. No brand deck attached. No guidelines document uploaded. No 40-page briefing
> template filled in. The system already has all of that. It has been reading Boozt's world —
> and building a knowledge base around it — for months.
>
> I'll hit Generate."

**[Click the Generate button. Pause. Let the pipeline start visibly before speaking again.]**

---

# SCENE 5 — UI TO HARNESS: HOW THEY CONNECT

**[Agent pipeline cards start animating. First card lighting up.]**

> "The moment I hit Generate, the frontend makes a single HTTP POST request to the Harness —
> our Python backend, running on Cloud Run.
>
> But this is not a standard request and response. The frontend opens a
> **Server-Sent Events** connection — a real-time, one-way stream from the server
> to the browser.
>
> Every update you see on screen — every agent card lighting up, every piece of content
> appearing — is being pushed live from the backend as it happens. There is no polling.
> There is no page refresh. It is a genuine live feed.
>
> The Harness receives the brief, identifies Boozt as the brand, and immediately kicks off
> the agent pipeline — running as a **Google ADK Workflow** — a directed acyclic graph of
> agent nodes, each with its own tools, its own instructions, and its own role."

---

# SCENE 6 — LOGOS: THE BRIEFING AGENT

**[Logos card is highlighted — loading indicator visible.]**

> "The first node to execute is **Logos** — but before Logos even starts reasoning, a
> deterministic function node called `load_brand_context` runs first.
>
> This function node does three things simultaneously.

---

### Data Pull 1 — Brand Guidelines (GCS + Cloud SQL + pgvector)

> "Boozt's brand guidelines document lives in a **Google Cloud Storage bucket**.
> It has also been chunked into 58 text segments, and each segment has been embedded
> using **Gemini Embedding 2** — Google's latest embedding model — producing a
> 768-dimensional vector for every chunk.
>
> Those 58 vectors are stored in **Cloud SQL** — a managed PostgreSQL instance —
> with the **pgvector extension** installed. This turns a relational database into
> a semantic search engine.
>
> When Logos needs brand context, it doesn't do a keyword search. It takes your brief,
> embeds it using the same Gemini model, and runs a **cosine similarity search** across
> all 58 brand guideline chunks. It retrieves the most semantically relevant sections —
> positioning, tone of voice, forbidden terms — even when the exact words don't match.

---

### Data Pull 2 — Fan Truths (pgvector)

> "Fan Truths are validated consumer beliefs — real things that people in the target
> audience genuinely feel about energy drinks and the Boozt brand. Examples like:
>
> *'That first sip when you need to switch on — that's a Boozt moment.'*
>
> *'Peak performance isn't a personality. It's a decision you make every day.'*
>
> These truths are also stored as vectors in pgvector and retrieved by semantic
> similarity to your brief. So Logos finds the truths that are most relevant to a
> festival campaign — not just any truth about any energy drink.

---

### Data Pull 3 — Campaign Benchmarks (Cloud SQL)

> "Finally — historical performance data from past Boozt campaigns.
> Click-through rates. ROAS. Engagement rates. Reach figures. Budget ranges.
> All pulled from Cloud SQL. This grounds the strategy in what has actually worked before —
> not what sounds good on paper.
>
> All three data pulls happen before Logos writes a single word. Then Logos packages
> everything into a structured typed object — a BriefingContext — and passes it to
> the next agent in the graph."

---

# SCENE 7 — HELIA: STRATEGY AND FAN TRUTH SCORE

**[Helia card lights up. Fan Truth gauge appears on screen.]**

> "**Helia** — the strategy agent — receives Logos's briefing package and builds the
> creative territory.
>
> But watch this number appearing on screen. This is the **Fan Truth Score**.
> It is our quality gate.
>
> Helia evaluates its proposed creative strategy against the Fan Truth database and
> produces a score out of 100. You can see we're sitting at 84 — and the verdict
> is **PASS**."

**[Pause. Let the audience look at the score.]**

> "What does PASS mean?
>
> It means the campaign idea — the territory, the language, the emotional angle —
> resonates with something the target audience genuinely believes. Not what Boozt
> wants them to believe. What 18 to 28 year olds who drink energy drinks at festivals
> actually feel.
>
> If this had come back as FAIL — if the strategy was too generic, too feature-focused,
> or contradicted real audience sentiment — the system would flag it. The campaign
> does not progress until the idea is strong enough.
>
> This is AI working as a **creative quality filter** — not just a content generator."

---

# SCENE 8 — IDEON: THE COPY AGENT

**[Ideon card lights up. Copy panel appears.]**

> "**Ideon** writes the copy.
>
> It has the brand guidelines — including Boozt's forbidden terms.
> No generic energy-drink clichés. No 'boost your day.' No references to any previous
> brand positioning. Ideon knows what it cannot say — and that shapes what it does say.
>
> The headline it produces: **'Zero limits. Pure energy.'**
>
> Short. Punchy. Emotionally true to the brand.
>
> Ideon also writes the medium headline for digital, the long-form body copy,
> and the CTA — all consistent with each other, all anchored in the strategy
> Helia defined."

---

# SCENE 9 — AETHER: CULTURAL INTELLIGENCE

**[Aether card lights up. Cultural insight panel appears.]**

> "**Aether** runs cultural intelligence.
>
> It analyses what is happening in culture right now that is relevant to this brief.
>
> Festival culture is peaking post-pandemic. Performance lifestyle content is dominating
> Gen Z feeds. The boundary between working hard and living hard is dissolving —
> and Boozt sits exactly in that gap.
>
> Aether's insight gets woven into the strategy, the copy brief, and the visual direction.
> This is what stops campaigns from feeling generic — campaigns that could be for any brand,
> any product, any moment."

---

# SCENE 10 — MORPHIS: THE VISUAL AGENT

**[Morphis card lights up. Key visual image appears in the panel.]**

> "**Morphis** generates the key visual.
>
> It takes the creative territory from Helia, the copy direction from Ideon,
> and the cultural context from Aether — and constructs a detailed image generation
> prompt for **Gemini's image model**.
>
> The result — you can see it loading now — is a brand-aligned campaign visual.
> Festival crowd. Golden hour. Boozt can, front and centre. Athletes, energy, movement.
>
> Not stock photography. Not a generic gym image. A proper campaign key visual —
> generated from your brief, in real time."

---

# SCENE 11 — KINETIK: THE VIDEO AGENT

**[Kinetik card lights up. Video player appears.]**

> "**Kinetik** produces the campaign reel.
>
> A six-second video — live generated, streamed back from the backend, embedded
> directly in the browser. You can press play right now.
>
> Fast cuts. High energy. Designed to land before the thumb scrolls past.
> Optimised for TikTok and Instagram Reels.
>
> The entire video was generated from the same brief — no storyboard, no brief to
> a video team, no edit suite."

---

# SCENE 12 — POLY: CHANNEL ADAPTATION

**[Poly card lights up. Channel panels for Instagram, TikTok, Google Ads, Email appear.]**

> "Finally — **Poly**. This is where the campaign gets deployed across platforms.
>
> Poly takes everything — strategy, copy, visual, video — and adapts it for
> four channels simultaneously.
>
> Instagram caption — with hashtags, conversational tone, optimised for the grid.
>
> TikTok hook and script — opening line in the first two seconds, fast pacing,
> authentic voice.
>
> Google Ads — headline in 30 characters. Description in 90. Poly counts characters.
> It won't exceed the limit.
>
> Email — subject line designed for open rate, body copy for click-through.
>
> Every adaptation follows the platform's format rules, character limits, and best
> practices. All of it — automatically. Zero manual work."

---

# SCENE 13 — BIGQUERY: THE DATA LAYER

**[Pipeline complete. Optionally switch to BigQuery console tab briefly.]**

> "While that entire pipeline was running — silently, in the background — every event
> was being logged to **BigQuery**.
>
> The brief. The brand. Which agents ran. The Fan Truth score. The model used.
> Latency per agent. Output token counts. All landing in our BigQuery dataset in real time.
>
> This means we can answer questions no campaign platform has ever been able to answer:
>
> Which creative territories score highest for Boozt — consistently, over time?
> What is the average Fan Truth score by brand, by season, by channel?
> Where does the pipeline take the longest — and why?
>
> The data is there. Queryable. Immediately. No separate analytics tool.
> No manual reporting layer."

---

# SCENE 14 — THE RESULTS WALKTHROUGH

**[Scroll through the full results panel slowly. Pause at each section.]**

> "Let me show you what we have — in full.
>
> **Fan Truth Score — 84. PASS.**
> The idea is grounded in real audience belief. It would not have made it through if it wasn't.
>
> **Creative strategy —** the positioning, the territory, the pillars.
> Built by Helia, validated by audience data.
>
> **Headlines and copy —** short, medium, long. Written by Ideon.
> Brand-correct, brief-correct, human-quality.
>
> **Key visual —** generated by Morphis using Gemini.
> One prompt. One image. Campaign-ready.
>
> **Campaign reel —** six seconds. Generated by Kinetik.
> Press play. That is your TikTok ad.
>
> **Channel adaptations —** Instagram, TikTok, Google Ads, Email.
> Adapted by Poly. Ready to copy and paste into your publishing tools."

**[Pause. Let the audience absorb the full output.]**

---

# SCENE 15 — THE CLOSE

**[Full results visible. Speak slowly and deliberately.]**

> "In under three minutes — seven AI agents produced a complete campaign package.
>
> From one paragraph of brief.
>
> But here is what I want you to take away — what did **not** happen today.
>
> Nobody uploaded a brand deck.
> Nobody filled out a creative brief template.
> Nobody told the system that Boozt is an energy drink.
> Nobody manually wrote a Google Ads headline that fits in 30 characters.
> Nobody checked that the copy avoided forbidden terms.
>
> The system knew. Because the knowledge was already there.
> In GCS. In Cloud SQL. In Vertex AI Search.
> Embedded. Indexed. Ready.
>
> CampaignOS is not a chatbot. It is not a prompt-and-response tool.
>
> It is a multi-agent, knowledge-grounded, enterprise-grade campaign intelligence platform.
> Built on Google Cloud. Powered by Gemini. Orchestrated by ADK.
>
> And what you just saw is the beginning.
>
> Thank you."

---

---

# ANTICIPATED Q&A — QUICK ANSWERS

| Question | Answer |
|---|---|
| **"What if brand guidelines change?"** | Upload the new file to GCS, re-run the embedding indexer — next campaign reflects the update. Zero code change required. |
| **"How is this different from ChatGPT?"** | ChatGPT has no brand memory, no Fan Truth validation, no campaign benchmarks, no channel rules. CampaignOS is grounded in your specific brand data — it cannot go off-brand. |
| **"Can we add our own brand?"** | Yes. Drop the guidelines document in GCS, run the embedding script, and the brand is indexed and live. Takes about ten minutes. |
| **"What AI models does it use?"** | Gemini 2.0 Flash for generation, Gemini Embedding 2 for semantic vectors, with Groq / LLaMA 3.3 as a cost-optimised fallback route. |
| **"Is the data secure?"** | All data stays within your GCP project. Brand guidelines never leave Google Cloud. Nothing goes to a third-party API without your explicit configuration. |
| **"What is the Fan Truth score based on?"** | A curated library of validated consumer beliefs, stored as 768-dimensional vectors in pgvector. The campaign strategy is scored by cosine similarity to truths the audience actually holds — not brand claims. |
| **"Can it handle multiple brands simultaneously?"** | Yes. The architecture is brand-agnostic. Each brand has its own namespace in GCS and its own vector space in pgvector. |
| **"What's next for the platform?"** | The same architecture can extend to media planning agents, social listening agents, performance prediction, localisation, and legal review — all as additional nodes in the same workflow graph. |

---

---

# TECHNICAL REFERENCE — INFRASTRUCTURE SUMMARY

| Component | Technology | Role |
|---|---|---|
| Frontend | React + TypeScript + Vite | Campaign brief input, live pipeline streaming, results display |
| Backend (Harness) | Python + Google ADK | Workflow orchestration, agent execution, tool calls |
| Deployment | Google Cloud Run | Serverless, auto-scaling, both frontend and harness |
| CI/CD | Google Cloud Build | Build, push, deploy on commit |
| Brand Storage | Google Cloud Storage | Brand guidelines, product images, campaign assets |
| Vector Database | Cloud SQL (PostgreSQL + pgvector) | Brand guidelines chunks, fan truths, campaign benchmarks as 768-dim vectors |
| Embedding Model | Gemini Embedding 2 | 768-dimensional semantic vectors for RAG search |
| Live Search | Vertex AI Search | Managed brand rules and fan truth retrieval in production |
| Analytics | BigQuery | Real-time pipeline event logging, campaign performance data |
| Image Generation | Gemini Image Model | Key visual generation from campaign brief |
| LLM (primary) | Gemini 2.0 Flash | All agent reasoning and content generation |
| LLM (fallback) | Groq / LLaMA 3.3 70B | Cost-optimised fallback route via LiteLLM |
| Secrets | Google Secret Manager | API keys, database credentials |

---

*CampaignOS — Built by Infosys Aster. Powered by Google Cloud.*
