import asyncio
from sqlalchemy import select
from backend.database import AsyncSessionLocal
from backend.models import Topic

CATEGORIES_METADATA = {
    "Animal Health Monitoring": {
        "keywords": ["veterinary telemetry", "livestock biometric tracking", "canine sensor monitor", "animal health monitoring"],
        "weight": 6
    },
    "Artificial Intelligence": {
        "keywords": ["medical artificial intelligence", "clinical neural network", "healthcare AI model", "generative clinical AI"],
        "weight": 10
    },
    "Assistive Devices": {
        "keywords": ["assistive mobility exoskeleton", "smart prosthetic limb", "sensory assistive device", "adaptive medical technology"],
        "weight": 7
    },
    "Augmented Reality": {
        "keywords": ["augmented reality surgical navigation", "AR intraoperative display", "holographic anatomy visualization", "AR clinical simulation"],
        "weight": 8
    },
    "Biotechnology": {
        "keywords": ["biotechnology therapeutic vector", "recombinant biomanufacturing", "mRNA delivery lipid", "synthetic biology therapy"],
        "weight": 9
    },
    "Bone & Body Health": {
        "keywords": ["osteoporosis bone density", "musculoskeletal regeneration", "orthopedic osteointegration", "calcium metabolic health"],
        "weight": 7
    },
    "Top Stories": {
        "keywords": ["top medical breakthroughs", "major healthcare headlines", "pivotal clinical trial results", "urgent biomedical news"],
        "weight": 9
    },
    "Cardiovascular": {
        "keywords": ["transcatheter aortic valve", "heart failure clinical therapy", "myocardial infarction biomarker", "cardiovascular hemodynamic repair"],
        "weight": 9
    },
    "Communication Technology": {
        "keywords": ["hospital communication technology", "clinical secure messaging", "interoperable physician paging", "EHR communication integration"],
        "weight": 6
    },
    "Consumer Healthcare": {
        "keywords": ["consumer digital health", "over-the-counter diagnostic", "home biometric wellness test", "preventive consumer wellness"],
        "weight": 7
    },
    "Dental Care": {
        "keywords": ["digital dentistry 3D imaging", "periodontal antimicrobial therapy", "guided dental implantology", "enamel remineralization"],
        "weight": 6
    },
    "Dermatology": {
        "keywords": ["melanoma dermoscopy AI", "psoriasis biologic inhibitor", "atopic dermatitis targeted therapy", "topical clinical dermatology"],
        "weight": 8
    },
    "Diabetic Care": {
        "keywords": ["continuous glucose monitoring CGM", "automated insulin delivery loop", "type 2 diabetes GLP-1", "diabetic retinopathy screening"],
        "weight": 9
    },
    "Diagnostics": {
        "keywords": ["rapid molecular diagnostic", "point-of-care clinical test", "liquid biopsy biomarker", "computational diagnostic accuracy"],
        "weight": 9
    },
    "Digital Health Transformation": {
        "keywords": ["digital health transformation", "cloud clinical workflow", "hospital IT infrastructure", "decentralized healthcare technology"],
        "weight": 8
    },
    "Drug Discovery And Development": {
        "keywords": ["small molecule drug discovery", "Phase clinical trial candidate", "computational protein docking", "novel pharmaceutical development"],
        "weight": 10
    },
    "Electromedicine": {
        "keywords": ["transcranial magnetic stimulation", "bioelectric neural pacing", "electromedicine therapeutic pulse", "deep brain stimulation"],
        "weight": 7
    },
    "Electronic Health Records": {
        "keywords": ["electronic health records EHR interoperability", "clinical documentation AI", "FHIR API integration", "EHR diagnostic workflow"],
        "weight": 8
    },
    "Endocrinology": {
        "keywords": ["thyroid hormone regulation", "endocrine pituitary adenoma", "metabolic syndrome therapeutics", "hormonal receptor signaling"],
        "weight": 7
    },
    "Endoscopy": {
        "keywords": ["AI computer-aided endoscopy", "video capsule endoscopy", "gastrointestinal polyp detection", "flexible endoscopic resection"],
        "weight": 7
    },
    "ePatient": {
        "keywords": ["epatient digital empowerment", "patient portal health engagement", "participatory medicine", "patient-reported health outcome"],
        "weight": 6
    },
    "Ergonomics": {
        "keywords": ["surgical ergonomic instrumentation", "occupational healthcare ergonomics", "hospital workstation design", "repetitive strain prevention"],
        "weight": 5
    },
    "Featured": {
        "keywords": ["featured medical innovation", "premier healthcare technology", "flagship clinical investigation", "groundbreaking therapeutic review"],
        "weight": 8
    },
    "Genomics": {
        "keywords": ["whole genome sequencing WGS", "CRISPR base editing therapeutic", "somatic mutation panel", "functional genomics variant"],
        "weight": 10
    },
    "Headlines News": {
        "keywords": ["global medical headlines", "health policy breaking news", "FDA advisory committee decision", "biopharma market regulatory"],
        "weight": 8
    },
    "Health Sensors & Trackers": {
        "keywords": ["photoplethysmography PPG sensor", "continuous vital sign tracker", "implantable bioimpedance sensor", "continuous telemetry patch"],
        "weight": 8
    },
    "Health Wearables": {
        "keywords": ["smartwatch ECG arrhythmia detection", "wearable pulse oximetry", "clinical grade wearable patch", "sleep apnea biometric wearable"],
        "weight": 8
    },
    "Healthcare Software": {
        "keywords": ["clinical decision support software", "hospital management SaaS", "medical imaging PACS software", "telehealth cloud infrastructure"],
        "weight": 8
    },
    "Hospital Management": {
        "keywords": ["hospital capacity management", "inpatient bed allocation AI", "emergency triage throughput", "clinical staffing optimization"],
        "weight": 7
    },
    "Hot This Week": {
        "keywords": ["trending health news this week", "breakthrough study published", "urgent healthcare bulletin", "viral medical research discovery"],
        "weight": 8
    },
    "Image Analysis": {
        "keywords": ["deep learning medical imaging", "radiology automated segmentation", "digital pathology slide analysis", "optical coherence tomography AI"],
        "weight": 9
    },
    "Immunography": {
        "keywords": ["immunotherapy profiling", "multiplex immune biomarker mapping", "T-cell receptor spatial immunography", "CAR-T response mapping"],
        "weight": 8
    },
    "Infection Control": {
        "keywords": ["antimicrobial stewardship", "hospital-acquired infection prevention", "pathogen genomic surveillance", "ultraviolet sterilization clinical"],
        "weight": 8
    },
    "Insight": {
        "keywords": ["clinical editorial perspective", "healthcare industry analysis", "physician survey insight", "health economics forecast"],
        "weight": 7
    },
    "Laboratory Equipment": {
        "keywords": ["automated clinical laboratory analyzer", "high-throughput flow cytometry", "mass spectrometry diagnostic", "microfluidic lab-on-a-chip"],
        "weight": 7
    },
    "Lifestyle Medicine": {
        "keywords": ["lifestyle medicine chronic disease", "nutritional intervention trial", "cardiovascular exercise metabolic", "preventive longevity protocol"],
        "weight": 7
    },
    "Medical Billing": {
        "keywords": ["ICD-10 clinical coding AI", "medical billing claims automation", "revenue cycle management RCM", "prior authorization turnaround"],
        "weight": 6
    },
    "Medical devices": {
        "keywords": ["FDA 510k medical device clearance", "implantable therapeutic hardware", "class III medical device trial", "biomedical sensor hardware"],
        "weight": 9
    },
    "Mental Health": {
        "keywords": ["psychiatric digital therapeutics", "major depressive disorder clinical trial", "PTSD neuromodulation", "cognitive behavioral digital therapy"],
        "weight": 9
    },
    "Molecular Diagnostic": {
        "keywords": ["polymerase chain reaction PCR multiplex", "circulating tumor DNA ctDNA", "next-generation sequencing diagnostic", "in vitro molecular assay"],
        "weight": 9
    },
    "Must Read": {
        "keywords": ["essential clinical review", "landmark medical trial publication", "gold-standard health guidelines", "unanimous clinical consensus"],
        "weight": 8
    },
    "Nanotechnology": {
        "keywords": ["nanoparticle targeted drug delivery", "nanomedicine oncology therapeutic", "gold nanoparticle biosensor", "lipid nanoparticle formulation"],
        "weight": 9
    },
    "Nephrology": {
        "keywords": ["chronic kidney disease CKD progression", "hemodialysis vascular graft", "renal transplant rejection biomarker", "diabetic nephropathy trial"],
        "weight": 8
    },
    "News": {
        "keywords": ["medical news update", "clinical trial announcement", "public health bulletin", "biomedical discovery report"],
        "weight": 7
    },
    "Oncology": {
        "keywords": ["checkpoint inhibitor immunotherapy", "bispecific antibody oncology", "solid tumor precision oncology", "antibody-drug conjugate ADC trial"],
        "weight": 10
    },
    "Pain Management": {
        "keywords": ["non-opioid analgesic trial", "spinal cord stimulation neuromodulation", "neuropathic pain intervention", "interventional pain management"],
        "weight": 8
    },
    "Patient Communication": {
        "keywords": ["secure patient communication", "multilingual clinical translation AI", "discharge instruction clarity", "patient engagement messaging"],
        "weight": 6
    },
    "Patient Engagement": {
        "keywords": ["patient engagement adherence", "remote clinical monitoring compliance", "mobile health gamification", "shared decision making tool"],
        "weight": 7
    },
    "Patient Monitoring": {
        "keywords": ["remote patient monitoring RPM", "continuous inpatient telemetry", "early clinical deterioration warning", "ICU hemodynamic monitoring"],
        "weight": 9
    },
    "Personal Health Record": {
        "keywords": ["personal health record PHR app", "patient data sovereignty", "Apple HealthKit EHR sync", "consumer medical history access"],
        "weight": 6
    },
    "Pharmacy Management": {
        "keywords": ["pharmacy dispensing automation", "medication adherence monitoring", "clinical pharmacy reconciliation", "drug supply chain traceability"],
        "weight": 7
    },
    "Physical Therapy": {
        "keywords": ["robotic physical therapy rehabilitation", "musculoskeletal gait analysis", "post-stroke motor recovery", "neuromuscular physical rehabilitation"],
        "weight": 7
    },
    "Popular": {
        "keywords": ["trending health articles", "widely read clinical studies", "popular medical innovations", "viral healthcare discoveries"],
        "weight": 7
    },
    "Population Health Management": {
        "keywords": ["population health predictive risk", "social determinants of health SDOH", "chronic disease registry", "preventive community health metric"],
        "weight": 8
    },
    "Portable Diagnostics": {
        "keywords": ["handheld point-of-care ultrasound POCUS", "portable blood chemistry analyzer", "smartphone diagnostic reader", "field triage diagnostic device"],
        "weight": 8
    },
    "Press Release": {
        "keywords": ["biopharma corporate press release", "medical device commercial launch", "clinical trial enrollment initiation", "regulatory filing clearance"],
        "weight": 6
    },
    "Profile": {
        "keywords": ["physician scientist profile", "medical innovator interview", "healthcare founder perspective", "clinical researcher spotlight"],
        "weight": 6
    },
    "Prosthetics": {
        "keywords": ["myoelectric bionic prosthesis", "osseointegrated limb prosthetic", "targeted muscle reinnervation TMR", "neural-interfaced bionic hand"],
        "weight": 8
    },
    "Protein Solution": {
        "keywords": ["protein structure prediction AlphaFold", "de novo computational protein design", "monoclonal antibody crystallization", "protein stability formulation"],
        "weight": 9
    },
    "Public Health": {
        "keywords": ["epidemiological surveillance bulletin", "vaccine efficacy population trial", "global health outbreak tracking", "preventive community screening"],
        "weight": 8
    },
    "Recent": {
        "keywords": ["latest clinical investigation", "newly published medical paper", "recent health authority clearance", "fresh biotech clinical data"],
        "weight": 7
    },
    "Robotics": {
        "keywords": ["robotic surgical console", "autonomous microsurgical robot", "laparoscopic robotic articulation", "rehabilitation robotic exoskeleton"],
        "weight": 9
    },
    "Spine Devices": {
        "keywords": ["interbody spinal fusion cage", "minimally invasive spine MIS device", "cervical artificial disc replacement", "robotic spine pedicle screw"],
        "weight": 8
    },
    "Surgical Devices": {
        "keywords": ["energy surgical vessel sealing", "minimally invasive surgical trocar", "intraoperative fluorescence guidance", "ultrasonic surgical aspirator"],
        "weight": 8
    },
    "Telemedicine": {
        "keywords": ["virtual synchronous consultation", "telehealth reimbursement parity", "asynchronous tele-specialty care", "direct-to-consumer telemedicine"],
        "weight": 9
    },
    "Trending": {
        "keywords": ["trending medical breakthrough", "viral clinical discovery", "rapidly cited health research", "front-page healthcare news"],
        "weight": 7
    },
    "Uncategorized": {
        "keywords": ["general biomedical discovery", "interdisciplinary health science", "novel healthcare paradigm", "translational medicine"],
        "weight": 5
    },
    "Virtual Reality": {
        "keywords": ["immersive virtual reality surgery", "VR pain distraction therapy", "virtual reality surgical training", "VR neuro-rehabilitation cognitive"],
        "weight": 8
    },
    "Xclusive Articles": {
        "keywords": ["exclusive investigative health report", "premier clinical breakthrough reveal", "behind-the-scenes biopharma trial", "in-depth medical analysis"],
        "weight": 8
    }
}

async def seed_all_categories():
    async with AsyncSessionLocal() as session:
        print(f"Checking database for {len(CATEGORIES_METADATA)} categories...")
        added_count = 0
        updated_count = 0

        for name, meta in CATEGORIES_METADATA.items():
            res = await session.execute(select(Topic).where(Topic.name == name))
            existing = res.scalars().first()
            if existing:
                # Update keywords if empty
                if not existing.keywords or len(existing.keywords) == 0:
                    existing.keywords = meta["keywords"]
                    existing.weight = meta["weight"]
                    updated_count += 1
            else:
                topic = Topic(
                    name=name,
                    keywords=meta["keywords"],
                    weight=meta["weight"],
                    is_active=True,
                    domain_whitelist=["nature.com", "nejm.org", "thelancet.com", "jamanetwork.com", "fda.gov"],
                    lookback_days=7
                )
                session.add(topic)
                added_count += 1

        await session.commit()
        print(f"Done! Added {added_count} new topics, updated {updated_count} existing topics.")

if __name__ == "__main__":
    asyncio.run(seed_all_categories())
