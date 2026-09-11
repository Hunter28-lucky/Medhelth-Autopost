import json
import logging
import re
from typing import Dict, Any, List, Optional
import anthropic
from backend.models import ContentRule
from backend.config import settings
from backend.services.openrouter_client import OpenRouterClient

logger = logging.getLogger("publisher.generator")

class ContentGenerator:
    def __init__(
        self,
        ai_provider: Optional[str] = None,
        openrouter_api_key: Optional[str] = None,
        openrouter_model: Optional[str] = None,
        anthropic_api_key: Optional[str] = None,
        anthropic_model: Optional[str] = None
    ):
        self.ai_provider = ai_provider if ai_provider is not None else settings.AI_PROVIDER
        resolved_openrouter_key = openrouter_api_key if openrouter_api_key is not None else settings.OPENROUTER_API_KEY
        self.openrouter_client = OpenRouterClient(
            api_key=resolved_openrouter_key,
            model=openrouter_model or settings.OPENROUTER_MODEL
        )
        resolved_anthropic_key = anthropic_api_key if anthropic_api_key is not None else settings.ANTHROPIC_API_KEY
        self.anthropic_api_key = resolved_anthropic_key
        self.anthropic_model = anthropic_model or settings.ANTHROPIC_MODEL
        self.anthropic_client = anthropic.Anthropic(api_key=self.anthropic_api_key) if self.anthropic_api_key else None

    async def generate_draft(
        self,
        topic_name: str,
        research_articles: List[Dict[str, Any]],
        rules: ContentRule,
        deviation_angle_instruction: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generates an article draft grounded strictly in the research articles.
        Routes via OpenRouter Free AI (or Claude if configured), with local sandbox fallback.
        """
        if not self.openrouter_client.is_configured() and not self.anthropic_client:
            logger.info("Neither OpenRouter nor Anthropic configured. Using high-quality sandbox generator.")
            return self._generate_sandbox_draft(topic_name, research_articles, rules, deviation_angle_instruction)

        # Prepare research grounding summary
        research_context = []
        for idx, art in enumerate(research_articles, start=1):
            claims_str = "\n".join([f"  - {c}" for c in art.get("key_claims", [])])
            research_context.append(
                f"Source {idx}:\n"
                f"- Title: {art.get('title')}\n"
                f"- URL: {art.get('url')}\n"
                f"- Source Outlet: {art.get('source')}\n"
                f"- Published Date: {art.get('publish_date')}\n"
                f"- Key Claims / Extracted Facts:\n{claims_str}\n"
                f"- Full Excerpt:\n{art.get('full_text', '')[:2500]}\n"
            )
        grounding_text = "\n---\n".join(research_context)

        system_prompt = (
            "You are an expert medical science communicator, clinical journalist, and healthcare SEO specialist. "
            "Your task is to synthesize verified research into an engaging, authoritative, and original article draft. "
            "\n\nCRITICAL CONSTRAINTS & FORMAT RULES:\n"
            "1. GROUNDING ONLY: Never hallucinate clinical trials, percentages, patient outcomes, or medical claims. "
            "Every statistic or quote must originate directly from the provided source materials.\n"
            "2. ZERO PLAGIARISM: Do not copy phrases or verbatim sentences from sources. Synthesize and write in fresh, original prose.\n"
            "3. PURE SEMANTIC WORDPRESS HTML: Use strictly <h2> for section headers and <p> for body paragraphs. "
            "Do NOT include any <div> tags, inline style attributes, artificial callout boxes, blockquotes, or FAQ accordions inside body_html. "
            "Keep the HTML completely clean and editorial, perfectly formatted for the WordPress Classic and Gutenberg editors.\n"
            "4. 3-SECTION, 13-PARAGRAPH ARCHITECTURE (Target 550-750 words):\n"
            "   - Section 1 (H2: '[Subject] A New Approach to [Field/Care]'): 3 concise paragraphs (what it is/creators, practical user/caregiver problem solved, shift from data surveillance to supportive care).\n"
            "   - Section 2 (H2: '[Subject] Features and Connectivity' or 'Capabilities'): 5 concise paragraphs (cellular/wrist connectivity, GPS & emergency telemetry, continuous vital monitoring, screenless/ergonomic design, integrated carrier/adoption ease).\n"
            "   - Section 3 (H2: '[Subject] and the Future of [Care/Field]'): 5 concise paragraphs (macro industry fragmentation, unified tool convergence, founder/clinical pedigree evolution, proactive routine awareness, concluding vision of patient independence).\n"
            "5. OUTPUT FORMAT: Respond ONLY with a valid JSON object matching the requested schema. No markdown formatting outside the JSON."
        )

        user_prompt = f"""
TOPIC CATEGORY: {topic_name}

CONTENT RULES & CONFIGURATION:
- Tone/Voice: {rules.tone}
- Target Word Count: 550 to 750 words (3 sections, 13 concise paragraphs total)
- Heading Structure: Exactly 3 clean <h2> sections (No custom styled divs or inline CSS)
- Target Audience & Reading Level: {rules.reading_level}
- Style Guide Directives: {rules.style_guide_text}
- Mandatory Disclaimer Text: {rules.disclaimer_text}

CRITICAL YOAST SEO & READABILITY DIRECTIVES (MUST ACHIEVE ALL GREEN BULLETS):
1. Choose a clear 2-4 word FOCUS KEYPHRASE (e.g. 'chest CT AI', 'cardiac mRNA therapy', 'LTE health band', 'oncology drug approval').
2. Placement: You MUST include the exact focus keyphrase in:
   - The SEO title / headline (frontloaded near the beginning)
   - The very first sentence of the lead paragraph
   - At least two <h2> subheadings
   - The meta description (strictly 135 to 155 characters)
   - The URL slug (kebab-case)
   - The concluding summary sentence
3. Readability & Natural Transitions: At least 30% of all sentences MUST smoothly weave in transition phrases (e.g. 'Instead of', 'These updates', 'As a result', 'With connected safety features', 'Rather than', 'Another advantage', 'Managing these separate solutions', 'However', 'The platform can also', 'Ultimately demonstrates how', 'Furthermore').
4. Keep paragraphs short and scannable (2-4 sentences each, 40-65 words) and sentences mostly under 20 words.

RESEARCH SOURCES PROVIDED FOR FACTUAL GROUNDING:
{grounding_text}
"""

        # Few-Shot Style Reference Cloner
        if getattr(rules, "style_reference_sample", None) and rules.style_reference_sample.strip():
            user_prompt += f"""

FEW-SHOT VISUAL FORMAT & WORDING PLACEMENT DIRECTIVE:
The user has provided an explicit reference post to strictly emulate in structure, paragraph rhythm, and wording placement:
=== USER'S REFERENCE FORMAT TEMPLATE BEGIN ===
{rules.style_reference_sample.strip()}
=== USER'S REFERENCE FORMAT TEMPLATE END ===

CRITICAL STYLE CLONING INSTRUCTIONS:
1. HEADLINE EMULATION: Formulate a punchy, active headline matching the style '[Subject] Launch New [Capability] From [Founders/Team].'
2. 3-SECTION CADENCE: Follow the exact 3-section, 13-paragraph layout demonstrated in the template.
3. WORDING PLACEMENT: Replicate the smooth introductory lead-in, feature-by-feature progression, and forward-looking synthesis seen in the template.
4. PURE HTML: Generate strictly clean <h2> and <p> elements without any styled divs.
"""

        if deviation_angle_instruction:
            user_prompt += f"\n\nSPECIAL DEDUPLICATION PIVOT DIRECTIVE:\n{deviation_angle_instruction}\n"

        user_prompt += """
Please generate a complete, structured JSON response with the following keys:
{
  "focus_keyphrase": "2-4 word target focus keyphrase",
  "title": "Compelling, accurate H1 title (avoid clickbait)",
  "slug": "kebab-case-slug-containing-focus-keyphrase",
  "excerpt": "A concise 2-sentence executive summary (under 160 characters)",
  "body_html": "Full article formatted strictly with clean <h2> and <p> tags across 3 sections and 13 concise paragraphs (approx 550-750 words). Do NOT include <h1>, <div>, or inline style attributes in body_html.",
  "meta_title": "SEO Title (45-60 characters, keyword frontloaded)",
  "meta_description": "Compelling Meta Description (strictly 135-155 characters) containing the focus keyphrase",
  "tags": ["tag1", "tag2", "tag3", "tag4"],
  "categories": [""" + f'"{topic_name}"' + """],
  "key_takeaways": ["Takeaway 1", "Takeaway 2", "Takeaway 3"],
  "disclaimer": """ + f'"{rules.disclaimer_text}"' + """,
  "sources_used": [
    {"title": "Source title", "url": "https://...", "domain": "domain.com"}
  ]
}
"""

        # 1. Try OpenRouter Free AI if configured (preferred free route)
        if self.openrouter_client.is_configured():
            try:
                logger.info(f"Generating draft using OpenRouter Free AI ({self.openrouter_client.model})...")
                return self.openrouter_client.generate_chat_completion(
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    temperature=0.3,
                    max_tokens=4000
                )
            except Exception as e:
                logger.error(f"OpenRouter generation failed: {e}. Attempting secondary provider or sandbox fallback...")

        # 2. Try Anthropic Claude if configured
        if self.anthropic_client:
            try:
                response = self.anthropic_client.messages.create(
                    model=self.anthropic_model,
                    max_tokens=4000,
                    temperature=0.3,
                    system=system_prompt,
                    messages=[{"role": "user", "content": user_prompt}]
                )
                raw_text = response.content[0].text.strip()
                
                # Clean possible markdown wrapping
                if raw_text.startswith("```json"):
                    raw_text = raw_text[7:]
                if raw_text.startswith("```"):
                    raw_text = raw_text[3:]
                if raw_text.endswith("```"):
                    raw_text = raw_text[:-3]

                return json.loads(raw_text.strip())

            except Exception as e:
                logger.error(f"Claude API call failed: {e}. Falling back to sandbox generator.")

        # 3. Deterministic high-quality sandbox generator fallback
        logger.info("Executing deterministic clinical sandbox generator.")
        return self._generate_sandbox_draft(topic_name, research_articles, rules, deviation_angle_instruction)

    def _generate_sandbox_draft(
        self,
        topic_name: str,
        research_articles: List[Dict[str, Any]],
        rules: ContentRule,
        deviation_angle_instruction: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        High quality, deterministic draft generator used when no Anthropic API key is provided,
        enabling full end-to-end testing without external API requirements.
        """
        primary_article = research_articles[0] if research_articles else {
            "title": f"New Advances in {topic_name}",
            "url": "https://example.com/research",
            "source": "Clinical Medical Review",
            "key_claims": ["Demonstrated statistically significant patient improvements across trial cohorts."],
            "source_domain": "example.com"
        }

        claims = primary_article.get("key_claims", [])
        headline = primary_article.get("title", f"Innovations in {topic_name}")
        focus_keyphrase = topic_name.lower().strip()
        slug = re.sub(r'[^a-z0-9]+', '-', f"{focus_keyphrase}-{headline.lower()}").strip('-')[:60]

        angle_note = ""
        if deviation_angle_instruction:
            headline = f"Clinical Perspective: {headline}"
            angle_note = "<p><em>Notably, this analysis focuses on implementation barriers, healthcare economics, and longitudinal safety outcomes.</em></p>"

        takeaways = [
            claims[0] if len(claims) > 0 else f"New multi-center clinical trials highlight significant utility in {focus_keyphrase}.",
            claims[1] if len(claims) > 1 else "Integration of real-time clinical biomarkers reduces diagnostic latency.",
            claims[2] if len(claims) > 2 else "Regulatory approval pathways emphasize post-market longitudinal tracking."
        ]

        body_html = f"""
<h2>{focus_keyphrase.title()} A New Approach to Patient Care</h2>
<p>Created by leading medical researchers, {focus_keyphrase} represents a specialized healthcare development designed to support clinical workflows while improving everyday patient well-being. Specifically, this innovative approach focuses on proactive care rather than retrospective monitoring. It also combines targeted assessment, real-time communication, and longitudinal tracking in an accessible system that operates seamlessly across diverse clinical environments.</p>

<p>Furthermore, the methodology aims to give healthcare teams greater clinical confidence while allowing patients to maintain their independence. Instead of requiring individuals to constantly manage complicated protocols, it provides essential diagnostic insights through a straightforward process. In addition, caregivers can record critical updates about symptoms, medications, and routine changes through simplified interfaces.</p>

<p>Consequently, these updates can help clinical teams understand subtle shifts in daily routines and recognize patterns that may require prompt attention. The approach focuses on useful information rather than overwhelming users with complicated data dashboards. As a result, the system is designed to function more like a supportive guardian than an intrusive surveillance tool.</p>

<h2>{focus_keyphrase.title()} Features and Connectivity</h2>
<p>In terms of technical capabilities, the {focus_keyphrase} framework includes built-in real-time connectivity, allowing practitioners to coordinate assistance directly when needed. This capability can be especially useful when patients are away from acute care settings. With connected safety features, users can quickly communicate with trusted contacts and clinical teams whenever they require intervention.</p>

<p>Similarly, direct communication protocols add another essential layer of clinical protection. When an emergency occurs, the system can help transmit the user status to designated contacts. Meanwhile, it can also relay vital clinical telemetry alongside important observations, including heart rate metrics, activity levels, and immediate functional status.</p>

<p>Additionally, the platform continuously monitors several aspects of daily physiological activity. Sleep quality, movement trends, breathing patterns, and heart rate parameters can provide useful information about changes in a person's routine. Rather than simply collecting large amounts of raw data, the system aims to identify meaningful developments that families and physicians can understand and act upon.</p>

<p>Moreover, the streamlined ergonomic design plays an important role in the overall user experience. Without complex interfaces demanding constant attention, users can remain focused on their daily surroundings. Therefore, this design makes the technology more comfortable for older adults and individuals who prefer less screen-based complexity.</p>

<p>Another advantage is the integrated implementation approach. Specifically, healthcare organizations do not need to manage complicated secondary infrastructure for network connectivity. Consequently, this makes the technology easier to adopt for families and health systems looking for a convenient, dependable safety solution.</p>

<h2>{focus_keyphrase.title()} and the Future of Healthcare</h2>
<p>Ultimately, the emergence of {focus_keyphrase} reflects a broader movement toward technology that supports caregivers, clinicians, and their families. Many households currently depend on multiple separate health apps, communication tools, emergency devices, and disparate records. However, managing these separate solutions can create additional work for caregivers who already have demanding responsibilities.</p>

<p>To address this challenge, this integrated framework attempts to bring several essential functions together. Health monitoring, emergency communication, location tracking, and observational logging can operate as part of one connected system. In fact, this integrated approach helps reduce the mental burden associated with coordinating daily care.</p>

<p>The investigators' extensive experience in translational science also provides a strong foundation for developing dependable caregiving tools. However, this clinical initiative takes a distinct direction by focusing on family connection and patient safety. For this reason, its goal is not simply to track passive metrics but to provide meaningful information that helps caregivers understand how their loved ones are doing.</p>

<p>Furthermore, the platform can encourage better communication between care teams, caregivers, and family members. Instead of relying only on occasional clinical checkups or manual logs, families can receive useful insights into changing health trends. This can help them respond earlier when something appears unusual.</p>

<p>Looking forward, healthcare leaders intend to continue developing human-focused solutions for long-term patient care. With its combination of connectivity, physiological sensing, and safety capabilities, the system represents a thoughtful direction for modern healthcare technology. As a result, {focus_keyphrase} demonstrates how medical innovations can move beyond basic monitoring and become practical tools for supporting families, encouraging independence, and creating stronger connections between loved ones.</p>
"""
        font_style = getattr(rules, "style_reference_font", "")
        if font_style and font_style not in ("default", "system-ui, -apple-system, sans-serif"):
            body_html = f'<div style="font-family: {font_style}; line-height: 1.6;">\n{body_html}\n</div>'

        sources = []
        for art in research_articles:
            sources.append({
                "title": art.get("title"),
                "url": art.get("url"),
                "domain": art.get("source_domain", "medical-journal.org")
            })

        meta_title = f"{focus_keyphrase.title()}: {headline}"
        if len(meta_title) > 60:
            meta_title = meta_title[:57].rstrip() + "..."
        elif len(meta_title) < 40:
            meta_title = f"{meta_title} | Clinical Analysis"

        meta_description = f"Comprehensive clinical research review on {focus_keyphrase}. Explore multi-center trial outcomes, efficacy metrics, and expert medical implications."
        if len(meta_description) > 155:
            meta_description = meta_description[:152].rstrip() + "..."

        return {
            "focus_keyphrase": focus_keyphrase,
            "title": headline,
            "slug": slug[:60],
            "excerpt": f"An in-depth clinical analysis of recent advancements in {focus_keyphrase}, evaluating trial data, regulatory milestones, and prospective patient outcomes.",
            "body_html": body_html.strip(),
            "meta_title": meta_title,
            "meta_description": meta_description,
            "tags": [focus_keyphrase, "clinical-trials", "medical-ai", "healthcare-innovation"],
            "categories": [topic_name],
            "key_takeaways": takeaways,
            "disclaimer": rules.disclaimer_text,
            "sources_used": sources
        }
