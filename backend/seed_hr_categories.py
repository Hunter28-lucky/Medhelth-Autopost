import asyncio
import logging
from sqlalchemy import select
from backend.database import AsyncSessionLocal
from backend.models import ManagedSite, Topic, ContentRule
from backend.config import settings

logger = logging.getLogger("publisher.seed_hr")

HR_CATEGORIES_METADATA = {
    "Administration Management": {
        "keywords": ["HR administration workflow", "workforce administrative management", "office administration policy", "personnel administration systems"],
        "weight": 7
    },
    "AI in HR": {
        "keywords": ["artificial intelligence in human resources", "generative AI workforce automation", "AI recruiting talent intelligence", "AI employee management software"],
        "weight": 10
    },
    "Applicant Tracking Systems": {
        "keywords": ["applicant tracking systems ATS", "candidate management software", "recruiting ATS automation", "talent pipeline tracking"],
        "weight": 9
    },
    "Blogs": {
        "keywords": ["HR leadership blog insights", "workforce trends commentary", "human resources management articles", "modern workplace analysis"],
        "weight": 6
    },
    "Change Management": {
        "keywords": ["organizational change management", "workforce transition strategy", "change management leadership", "enterprise agile transformation"],
        "weight": 8
    },
    "Compensation Management": {
        "keywords": ["executive compensation management", "salary benchmarking structures", "employee compensation packages", "total rewards strategy"],
        "weight": 9
    },
    "Corporate Advisory": {
        "keywords": ["corporate human capital advisory", "strategic workforce planning", "organizational design consulting", "boardroom HR advisory"],
        "weight": 7
    },
    "Diversity and Inclusion Management": {
        "keywords": ["diversity equity and inclusion DEI", "inclusive workplace culture", "neurodiversity hiring initiative", "DEI strategy corporate leadership"],
        "weight": 9
    },
    "editors pick": {
        "keywords": ["top HR executive insights", "featured workplace strategy", "premier human resources report", "editorial workforce analysis"],
        "weight": 8
    },
    "Employee Benefits": {
        "keywords": ["employee benefits packages", "health insurance perks workforce", "voluntary employee benefits", "modern fringe benefits corporate"],
        "weight": 9
    },
    "Employee Communication": {
        "keywords": ["internal employee communication", "workplace communication channels", "transparent corporate messaging", "employee dialogue collaboration"],
        "weight": 7
    },
    "Employee Engagement": {
        "keywords": ["employee engagement initiatives", "workforce motivation strategies", "employee pulse survey metrics", "retaining engaged talent"],
        "weight": 10
    },
    "Employee Expense Management": {
        "keywords": ["corporate expense management software", "employee travel expense reimbursement", "automated expense reporting HR", "per diem workforce expense policy"],
        "weight": 7
    },
    "Employee Experience Management": {
        "keywords": ["employee experience EX platform", "workplace journey mapping", "employee sentiment analysis", "holistic workplace experience"],
        "weight": 9
    },
    "Employee Health Management": {
        "keywords": ["workplace health management", "corporate employee wellness program", "preventative worker health policy", "occupational health services"],
        "weight": 8
    },
    "Employee Learning Management": {
        "keywords": ["learning management systems LMS", "employee upskilling programs", "corporate continuous learning", "workforce microlearning platforms"],
        "weight": 8
    },
    "Employee Monitoring": {
        "keywords": ["employee monitoring software", "workforce productivity tracking", "ethical employee surveillance policy", "remote employee activity analytics"],
        "weight": 7
    },
    "Employee Onboarding": {
        "keywords": ["employee onboarding workflow", "digital new hire onboarding", "onboarding orientation best practices", "remote employee onboarding checklist"],
        "weight": 9
    },
    "Employee Performance Management": {
        "keywords": ["performance appraisal systems", "continuous performance management", "employee KPI milestone review", "360-degree feedback performance"],
        "weight": 9
    },
    "Employee Satisfaction Management": {
        "keywords": ["employee job satisfaction index", "workplace morale improvement", "measuring employee satisfaction", "retention satisfaction drivers"],
        "weight": 8
    },
    "Employee Training": {
        "keywords": ["workplace employee training modules", "corporate skill development", "hands-on employee training", "leadership training programs"],
        "weight": 8
    },
    "Employee Wellbeing": {
        "keywords": ["workplace mental health wellbeing", "employee burnout prevention", "corporate wellness initiatives", "work-life balance wellbeing"],
        "weight": 9
    },
    "Employment Law": {
        "keywords": ["employment law regulations", "labor law compliance updates", "EEOC workplace compliance", "FLSA wage and hour employment law"],
        "weight": 9
    },
    "Employment Verification": {
        "keywords": ["employment background check verification", "Form I-9 employment verification", "E-Verify workforce screening", "credential employment verification"],
        "weight": 7
    },
    "Featured": {
        "keywords": ["featured HR innovations", "spotlight workforce leadership", "premier talent strategy", "top human capital achievements"],
        "weight": 8
    },
    "Financial Wellness": {
        "keywords": ["employee financial wellness programs", "retirement financial literacy workplace", "financial stress employee benefits", "emergency savings workplace perk"],
        "weight": 7
    },
    "Headline News": {
        "keywords": ["breaking HR news", "workforce industry headlines", "major employment news updates", "human resources market developments"],
        "weight": 8
    },
    "Hiring": {
        "keywords": ["hiring trends and strategies", "talent acquisition hiring pipeline", "effective hiring methodologies", "speed of hire metrics"],
        "weight": 9
    },
    "Hiring and Onboarding": {
        "keywords": ["hiring and onboarding integration", "streamlined recruitment to onboarding", "new hire lifecycle management", "seamless hiring experience"],
        "weight": 9
    },
    "Hot this week": {
        "keywords": ["trending HR stories this week", "hot workforce discussions", "viral workplace trends", "top people management news"],
        "weight": 8
    },
    "HR Reporting": {
        "keywords": ["HR analytics reporting", "workforce demographic metrics", "human capital KPI dashboards", "predictive HR reporting"],
        "weight": 8
    },
    "Human Capital Management": {
        "keywords": ["human capital management HCM cloud", "enterprise human capital strategy", "HCM workforce architecture", "human capital optimization"],
        "weight": 10
    },
    "Human Resource Management System": {
        "keywords": ["HRMS cloud platforms", "integrated HR management system", "HRMS enterprise software", "core HR technology stack"],
        "weight": 9
    },
    "Human Resources Compliance": {
        "keywords": ["HR regulatory compliance audit", "statutory HR compliance policies", "workplace harassment prevention compliance", "OSHA labor compliance"],
        "weight": 9
    },
    "Insights": {
        "keywords": ["strategic HR market insights", "workforce thought leadership", "future of work insights", "executive talent insights"],
        "weight": 8
    },
    "Labor Allocation": {
        "keywords": ["workforce labor allocation", "dynamic shift scheduling labor", "labor capacity planning", "efficient resource labor deployment"],
        "weight": 7
    },
    "Labour Management": {
        "keywords": ["labor relations management", "union workforce negotiations", "collective bargaining management", "fair labor standards compliance"],
        "weight": 8
    },
    "Must Read": {
        "keywords": ["must read HR articles", "essential people management guide", "critical workforce intelligence", "foundational HR strategies"],
        "weight": 8
    },
    "News": {
        "keywords": ["human resources industry news", "global employment developments", "workplace policy updates", "labor market news"],
        "weight": 8
    },
    "Payroll Management": {
        "keywords": ["automated payroll management", "payroll processing cycles", "multi-state payroll compliance", "global payroll management"],
        "weight": 9
    },
    "Payroll Tax": {
        "keywords": ["payroll tax withholding compliance", "FICA payroll tax regulations", "state unemployment tax SUTA", "payroll tax filing software"],
        "weight": 8
    },
    "Performance Management": {
        "keywords": ["strategic performance management", "employee OKR goal alignment", "annual performance review evolution", "agile performance coaching"],
        "weight": 9
    },
    "popular": {
        "keywords": ["popular HR topics", "widely read workforce management", "popular workplace leadership ideas", "high interest HR articles"],
        "weight": 7
    },
    "Position Management": {
        "keywords": ["position control headcount management", "organizational chart position budgeting", "job role hierarchy management", "workforce position requisition"],
        "weight": 7
    },
    "Pre Employment Screening": {
        "keywords": ["pre-employment background screening", "candidate drug testing screening", "criminal background check screening", "skills pre-employment assessment"],
        "weight": 8
    },
    "Press Release": {
        "keywords": ["HR technology press release", "workforce company announcements", "human resources corporate news release", "HCM software launch"],
        "weight": 6
    },
    "Professional Employer Organization": {
        "keywords": ["PEO co-employment services", "professional employer organization benefits", "outsourced PEO HR solutions", "small business PEO management"],
        "weight": 8
    },
    "Profile": {
        "keywords": ["chief people officer executive profile", "HR leader spotlight", "influential workplace executive profile", "people operations leader interview"],
        "weight": 7
    },
    "Recruitment": {
        "keywords": ["talent recruitment methodologies", "sourcing passive candidates", "campus recruitment programs", "executive recruitment headhunting"],
        "weight": 10
    },
    "Recruitment Process Outsourcing": {
        "keywords": ["recruitment process outsourcing RPO", "enterprise RPO workforce solutions", "outsourced talent acquisition", "end-to-end RPO strategy"],
        "weight": 8
    },
    "Remote Work": {
        "keywords": ["remote work policy framework", "hybrid workforce productivity", "remote employee engagement tools", "distributed team culture"],
        "weight": 9
    },
    "Retirement": {
        "keywords": ["employee 401k retirement benefits", "defined contribution pension plans", "phased retirement programs", "corporate retirement planning perks"],
        "weight": 7
    },
    "Talent Management": {
        "keywords": ["strategic talent management", "high-potential talent development", "succession planning talent pipeline", "retaining critical talent"],
        "weight": 10
    },
    "Time and Attendance Management": {
        "keywords": ["automated time and attendance software", "biometric time tracking workplace", "FLSA overtime tracking hours", "pto vacation attendance management"],
        "weight": 8
    },
    "Top Stories": {
        "keywords": ["top workplace stories", "leading human resources developments", "major corporate talent headlines", "defining workforce stories"],
        "weight": 8
    },
    "Trending": {
        "keywords": ["trending HR workplace topics", "emerging talent management patterns", "workforce innovation trends", "modern HR buzz"],
        "weight": 8
    },
    "Uncategorized": {
        "keywords": ["general human resources insights", "interdisciplinary workplace topics", "contemporary business operations", "organizational effectiveness"],
        "weight": 5
    },
    "Woman Leaders": {
        "keywords": ["women in executive leadership", "female corporate leadership development", "closing gender leadership gap", "women C-suite mentors"],
        "weight": 9
    },
    "Workforce Management": {
        "keywords": ["enterprise workforce management WFM", "workforce optimization software", "labor forecasting demand", "field workforce scheduling"],
        "weight": 10
    },
    "Xclusive Articles": {
        "keywords": ["exclusive HR investigative journalism", "confidential workforce case studies", "in-depth executive talent reports", "exclusive people analytics review"],
        "weight": 8
    }
}

HR_DOMAINS = [
    "shrm.org", "hrdive.com", "hrexecutive.com", "personneltoday.com",
    "worklife.news", "forbes.com", "hbr.org", "mckinsey.com", "reuters.com", "bloomberg.com"
]

async def seed_the_hr_review_site():
    """
    Seeds 'The HR Review' (https://thehrreview.com/) into ManagedSites,
    creates its isolated ContentRule, and populates all 60 verified categories.
    Guarantees strict isolation and zero collision with MedHealth Times.
    """
    async with AsyncSessionLocal() as session:
        # 1. Fetch or create 'The HR Review' ManagedSite
        site_res = await session.execute(
            select(ManagedSite).where(ManagedSite.slug == "thehrreview")
        )
        site = site_res.scalars().first()

        if not site:
            # Check if there is a site with wp_url matching thehrreview.com
            url_res = await session.execute(
                select(ManagedSite).where(ManagedSite.wp_url.like("%thehrreview.com%"))
            )
            site = url_res.scalars().first()

        if not site:
            site = ManagedSite(
                name="The HR Review",
                slug="thehrreview",
                wp_url="https://thehrreview.com",
                wp_api_key=settings.WORDPRESS_API_KEY,  # Uses configured sync key
                description="Strategic Human Resources, Workplace Leadership, Talent Management & HR Technology Publication",
                is_active=True,
                auto_push_to_wp=False,
                is_scheduler_enabled=False,
                schedule_interval_hours=6
            )
            session.add(site)
            await session.commit()
            await session.refresh(site)
            print(f"[Seed] Created ManagedSite #{site.id}: 'The HR Review' ({site.wp_url})")
        else:
            print(f"[Seed] Found existing ManagedSite #{site.id}: '{site.name}' ({site.wp_url})")

        # 2. Fetch or create isolated ContentRule for The HR Review
        rule_res = await session.execute(
            select(ContentRule).where(ContentRule.site_id == site.id)
        )
        rule = rule_res.scalars().first()

        if not rule:
            rule = ContentRule(
                site_id=site.id,
                name="Publishing Rules for The HR Review",
                is_active=True,
                tone="Authoritative, Strategic & Professional",
                reading_level="HR Executives, People Leaders & Business Professionals",
                word_count_min=450,
                word_count_max=520,
                heading_structure="<h6><strong>Heading Title</strong></h6>",
                include_takeaways=False,
                include_faq=False,
                include_disclaimer=False,
                include_quotes=False,
                include_sources=True,
                disclaimer_text="Disclaimer: This article on The HR Review is for informational and educational purposes only and does not constitute formal legal, financial, or human resources advisory. Organizations should consult licensed employment counsel or qualified HR consultants for specific corporate decisions.",
                style_guide_text="Maintain authoritative, research-backed HR journalism. Focus on human capital strategy, employment law compliance, talent acquisition, workplace technology, employee experience, and organizational development. Cite reputable workforce data, industry surveys, and real-world enterprise practices.",
                auto_push_to_wp=site.auto_push_to_wp,
                enforce_yoast_green=True
            )
            session.add(rule)
            await session.commit()
            print(f"[Seed] Created ContentRule for Site #{site.id} ('The HR Review')")
        else:
            print(f"[Seed] Existing ContentRule verified for Site #{site.id}")

        # 3. Seed all 60 categories for this specific site_id
        added_count = 0
        updated_count = 0

        for name, meta in HR_CATEGORIES_METADATA.items():
            res = await session.execute(
                select(Topic).where(Topic.site_id == site.id, Topic.name == name)
            )
            existing = res.scalars().first()

            if existing:
                # Refresh keywords if needed
                if not existing.keywords or len(existing.keywords) == 0:
                    existing.keywords = meta["keywords"]
                    existing.weight = meta["weight"]
                    existing.domain_whitelist = HR_DOMAINS
                    updated_count += 1
            else:
                topic = Topic(
                    site_id=site.id,
                    name=name,
                    keywords=meta["keywords"],
                    weight=meta["weight"],
                    is_active=True,
                    domain_whitelist=HR_DOMAINS,
                    lookback_days=7
                )
                session.add(topic)
                added_count += 1

        await session.commit()
        print(f"[Seed] The HR Review: Successfully added {added_count} new categories, updated {updated_count}. Total categories: {len(HR_CATEGORIES_METADATA)}")
        return {
            "site_id": site.id,
            "site_name": site.name,
            "added_categories": added_count,
            "total_categories": len(HR_CATEGORIES_METADATA)
        }

if __name__ == "__main__":
    asyncio.run(seed_the_hr_review_site())
