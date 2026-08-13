"""Generate a synthetic but realistic Lebanese job-posting corpus for development/demo.

This is NOT a claim about the real market. Real collectors can replace/augment these
records. Each record includes source metadata and Lebanese locations/companies.
"""

from __future__ import annotations

import hashlib
import json
import random
from datetime import date, timedelta
from pathlib import Path
from typing import Any

COMPANIES = [
    ("Bank Audi", "Finance"),
    ("BLOM Bank", "Finance"),
    ("Byblos Bank", "Finance"),
    ("Solidere", "Real Estate"),
    ("Malia Group", "Conglomerate"),
    ("Holdal Group", "Conglomerate"),
    ("ABC", "Retail"),
    ("Spinneys", "Retail"),
    ("Touch", "Telecom"),
    ("Alfa", "Telecom"),
    ("Ogero", "Telecom"),
    ("Middle East Airlines", "Aviation"),
    ("Cefinor", "Engineering"),
    ("Khatib & Alami", "Engineering"),
    ("Dar Al-Handasah", "Engineering"),
    ("Lahoud Engineering", "Engineering"),
    ("BATCO", "Construction"),
    ("Debbas Group", "Electrical"),
    ("INDEVCO", "Manufacturing"),
    ("Sannine", "Food & Beverage"),
    ("Café Najjar", "Food & Beverage"),
    ("LibanPack", "Manufacturing"),
    ("Murex", "Software"),
    ("FOO", "Software"),
    ("SE Factory", "Education/Tech"),
    ("Berytech", "Tech Hub"),
    ("UK Lebanon Tech Hub", "Tech Hub"),
    ("American University of Beirut", "Education"),
    ("LAU", "Education"),
    ("USJ", "Education"),
    ("ESA Business School", "Education"),
    ("Clever Advocacy", "Marketing"),
    ("Impact BBDO", "Marketing"),
    ("Roula Abdo Studio", "Architecture"),
    ("Erga Group", "Architecture"),
    ("MedLabs", "Healthcare"),
    ("AUBMC", "Healthcare"),
    ("Clemenceau Medical Center", "Healthcare"),
    ("BEMO", "Finance"),
    ("Fransabank", "Finance"),
]

LOCATIONS = [
    "Beirut",
    "Mount Lebanon",
    "Jounieh",
    "Byblos",
    "Tripoli",
    "Zahle",
    "Sidon",
    "Metn",
    "Keserwan",
    "Remote",
]

TEMPLATES: list[dict[str, Any]] = [
    {
        "category": "Automation Engineering",
        "titles": [
            "Automation Engineer",
            "Junior Automation Engineer",
            "Controls Engineer",
            "Industrial Automation Specialist",
            "PLC Programmer",
        ],
        "skills_required": ["PLC", "Siemens PLC", "TIA Portal"],
        "skills_preferred": ["SCADA", "HMI", "Industrial Networking", "SolidWorks", "Python"],
        "education": "Bachelor's degree in Electrical or Mechatronics Engineering",
        "experience": ["Internship", "Entry-level", "0-2 years", "2-5 years"],
        "blurb": (
            "We are seeking an automation engineer with experience in Siemens PLCs, "
            "TIA Portal and industrial communication protocols. Knowledge of SCADA/HMI "
            "and SolidWorks is an advantage. Based in {location}, Lebanon."
        ),
    },
    {
        "category": "Software Engineering",
        "titles": [
            "Software Engineer",
            "Backend Developer",
            "Full Stack Developer",
            "Junior Software Engineer",
            "Python Developer",
        ],
        "skills_required": ["Python", "SQL", "Git"],
        "skills_preferred": ["Docker", "AWS", "PostgreSQL", "React", "FastAPI"],
        "education": "Bachelor's in Computer Science or Software Engineering",
        "experience": ["Entry-level", "0-2 years", "2-5 years", "5+ years"],
        "blurb": (
            "Join our engineering team in {location}. Required: Python, SQL, and strong "
            "problem solving. Preferred: Docker, AWS, PostgreSQL, React. English is required."
        ),
    },
    {
        "category": "Web Development",
        "titles": [
            "Frontend Developer",
            "React Developer",
            "Web Developer",
            "Next.js Developer",
            "Full Stack Web Developer",
        ],
        "skills_required": ["JavaScript", "HTML", "CSS", "React"],
        "skills_preferred": ["TypeScript", "Next.js", "Node.js", "Tailwind"],
        "education": "Bachelor's in Computer Science or related field",
        "experience": ["Internship", "Entry-level", "0-2 years", "2-5 years"],
        "blurb": (
            "Looking for a web developer proficient in JavaScript, HTML, CSS and React. "
            "Experience with TypeScript and Next.js is preferred. Location: {location}."
        ),
    },
    {
        "category": "Data Science",
        "titles": [
            "Data Analyst",
            "Data Scientist",
            "Business Intelligence Analyst",
            "Junior Data Analyst",
        ],
        "skills_required": ["SQL", "Excel", "Python"],
        "skills_preferred": ["Power BI", "Tableau", "Machine Learning", "Pandas"],
        "education": "Bachelor's in Computer Science, Statistics, or Business",
        "experience": ["Entry-level", "0-2 years", "2-5 years"],
        "blurb": (
            "Data role requiring SQL, Excel and Python. Power BI or Tableau preferred. "
            "Machine Learning knowledge is a plus. Office in {location}."
        ),
    },
    {
        "category": "Artificial Intelligence",
        "titles": [
            "Machine Learning Engineer",
            "AI Engineer",
            "Computer Vision Engineer",
            "NLP Engineer",
        ],
        "skills_required": ["Python", "Machine Learning", "PyTorch"],
        "skills_preferred": ["Deep Learning", "TensorFlow", "Computer Vision", "NLP", "Docker"],
        "education": "Bachelor's or Master's in Computer Science / AI",
        "experience": ["0-2 years", "2-5 years", "5+ years"],
        "blurb": (
            "AI team hiring for ML experience with Python and PyTorch. Deep Learning, "
            "Computer Vision or NLP preferred. Based in {location}."
        ),
    },
    {
        "category": "Mechanical Engineering",
        "titles": [
            "Mechanical Design Engineer",
            "Mechanical Engineer",
            "CAD Designer",
            "Junior Mechanical Engineer",
        ],
        "skills_required": ["SolidWorks", "AutoCAD"],
        "skills_preferred": ["ANSYS", "GD&T", "CNC", "CATIA"],
        "education": "Bachelor's in Mechanical Engineering",
        "experience": ["Internship", "Entry-level", "0-2 years", "2-5 years"],
        "blurb": (
            "Mechanical engineer needed with SolidWorks and AutoCAD. ANSYS and GD&T "
            "are preferred. Position located in {location}, Lebanon."
        ),
    },
    {
        "category": "Electrical Engineering",
        "titles": [
            "Electrical Engineer",
            "Power Systems Engineer",
            "Junior Electrical Engineer",
            "Electrical Design Engineer",
        ],
        "skills_required": ["AutoCAD", "Power Systems"],
        "skills_preferred": ["PLC", "MATLAB", "Circuit Design", "ETAP"],
        "education": "Bachelor's in Electrical Engineering",
        "experience": ["Entry-level", "0-2 years", "2-5 years"],
        "blurb": (
            "Electrical engineering role requiring AutoCAD and power systems knowledge. "
            "PLC and MATLAB experience preferred. Location: {location}."
        ),
    },
    {
        "category": "Mechatronics Engineering",
        "titles": [
            "Mechatronics Engineer",
            "Junior Mechatronics Engineer",
            "Controls & Mechatronics Engineer",
        ],
        "skills_required": ["MATLAB", "SolidWorks", "PLC"],
        "skills_preferred": ["ROS", "Arduino", "Python", "Control Systems", "Sensors"],
        "education": "Bachelor's in Mechatronics Engineering",
        "experience": ["Internship", "Entry-level", "0-2 years"],
        "blurb": (
            "Mechatronics engineer with MATLAB, SolidWorks and PLC fundamentals. "
            "ROS, Arduino and Python are nice to have. Based in {location}."
        ),
    },
    {
        "category": "Robotics",
        "titles": ["Robotics Engineer", "Robotics Software Engineer", "Junior Robotics Engineer"],
        "skills_required": ["ROS", "Python", "C++"],
        "skills_preferred": ["Computer Vision", "Control Systems", "MATLAB", "Linux"],
        "education": "Bachelor's in Mechatronics, Robotics or Computer Engineering",
        "experience": ["Entry-level", "0-2 years", "2-5 years"],
        "blurb": (
            "Robotics role requiring ROS, Python and C++. Computer Vision and control "
            "systems preferred. Work from {location}."
        ),
    },
    {
        "category": "Cybersecurity",
        "titles": [
            "Cybersecurity Analyst",
            "Security Engineer",
            "SOC Analyst",
            "Junior Security Analyst",
        ],
        "skills_required": ["Network Security", "Linux"],
        "skills_preferred": ["Penetration Testing", "SIEM", "OWASP", "Python"],
        "education": "Bachelor's in Computer Science or Cybersecurity",
        "experience": ["Entry-level", "0-2 years", "2-5 years"],
        "blurb": (
            "Security position requiring network security and Linux. Penetration testing "
            "and SIEM experience preferred. Location {location}."
        ),
    },
    {
        "category": "Civil Engineering",
        "titles": ["Civil Engineer", "Site Engineer", "Structural Engineer", "Junior Civil Engineer"],
        "skills_required": ["AutoCAD"],
        "skills_preferred": ["Project Management", "Communication"],
        "education": "Bachelor's in Civil Engineering",
        "experience": ["Internship", "Entry-level", "0-2 years", "2-5 years"],
        "blurb": (
            "Civil engineering opportunity in {location}. AutoCAD required. Project "
            "management and strong communication skills preferred. Arabic and English required."
        ),
    },
    {
        "category": "Architecture",
        "titles": ["Architect", "Junior Architect", "Architectural Designer"],
        "skills_required": ["AutoCAD"],
        "skills_preferred": ["SolidWorks", "Project Management", "Communication"],
        "education": "Bachelor's in Architecture",
        "experience": ["Internship", "Entry-level", "0-2 years"],
        "blurb": (
            "Architecture studio in {location} seeking AutoCAD proficiency. Strong design "
            "portfolio and communication skills preferred."
        ),
    },
    {
        "category": "Business",
        "titles": [
            "Business Analyst",
            "Operations Coordinator",
            "Management Trainee",
            "Junior Business Analyst",
        ],
        "skills_required": ["Excel", "Communication"],
        "skills_preferred": ["Power BI", "Project Management", "SQL"],
        "education": "Bachelor's in Business or related field",
        "experience": ["Internship", "Entry-level", "0-2 years"],
        "blurb": (
            "Business role in {location}. Excel and communication required. Power BI and "
            "project management preferred. English and Arabic."
        ),
    },
    {
        "category": "Finance",
        "titles": ["Financial Analyst", "Accountant", "Junior Accountant", "Credit Analyst"],
        "skills_required": ["Excel", "Accounting"],
        "skills_preferred": ["Communication", "Power BI"],
        "education": "Bachelor's in Finance or Accounting",
        "experience": ["Entry-level", "0-2 years", "2-5 years"],
        "blurb": (
            "Finance position requiring Excel and accounting fundamentals. Power BI is a plus. "
            "Based in {location}. English required."
        ),
    },
    {
        "category": "Marketing",
        "titles": [
            "Marketing Coordinator",
            "Digital Marketing Specialist",
            "Social Media Manager",
            "Junior Marketer",
        ],
        "skills_required": ["Marketing", "Communication"],
        "skills_preferred": ["Excel", "Project Management"],
        "education": "Bachelor's in Marketing or Business",
        "experience": ["Internship", "Entry-level", "0-2 years"],
        "blurb": (
            "Marketing role in {location}. Digital marketing and communication required. "
            "English and Arabic preferred; French is an asset."
        ),
    },
    {
        "category": "Sales",
        "titles": ["Sales Representative", "Account Executive", "Sales Coordinator"],
        "skills_required": ["Sales", "Communication"],
        "skills_preferred": ["Excel", "Customer Service"],
        "education": "Bachelor's preferred",
        "experience": ["Entry-level", "0-2 years", "2-5 years"],
        "blurb": (
            "Sales opportunity in {location}. Strong communication and sales skills required. "
            "Customer service experience preferred."
        ),
    },
    {
        "category": "Human Resources",
        "titles": ["HR Coordinator", "Talent Acquisition Specialist", "HR Officer"],
        "skills_required": ["Communication", "Excel"],
        "skills_preferred": ["Project Management", "Customer Service"],
        "education": "Bachelor's in HR or Business",
        "experience": ["Entry-level", "0-2 years"],
        "blurb": (
            "HR role based in {location}. Communication and Excel required. Arabic, English "
            "and preferably French."
        ),
    },
    {
        "category": "Healthcare",
        "titles": ["Clinical Coordinator", "Healthcare Administrator", "Lab Technician"],
        "skills_required": ["Communication", "Customer Service"],
        "skills_preferred": ["Excel", "Teamwork"],
        "education": "Relevant Bachelor's degree",
        "experience": ["Entry-level", "0-2 years", "2-5 years"],
        "blurb": (
            "Healthcare position in {location}. Strong communication required. Teamwork and "
            "Excel preferred. Arabic and English."
        ),
    },
    {
        "category": "Electronics Engineering",
        "titles": [
            "Electronics Engineer",
            "Embedded Systems Engineer",
            "Junior Electronics Engineer",
        ],
        "skills_required": ["Circuit Design", "Embedded Systems", "C"],
        "skills_preferred": ["PCB", "Arduino", "MATLAB", "Python"],
        "education": "Bachelor's in Electronics or Electrical Engineering",
        "experience": ["Internship", "Entry-level", "0-2 years"],
        "blurb": (
            "Electronics role requiring circuit design, embedded systems and C. PCB and "
            "Arduino preferred. Location: {location}."
        ),
    },
]


def _job_id(seed: str) -> str:
    return "lb_" + hashlib.md5(seed.encode()).hexdigest()[:12]


def generate_jobs(n: int = 350, seed: int = 42) -> list[dict[str, Any]]:
    rng = random.Random(seed)
    jobs: list[dict[str, Any]] = []
    today = date.today()
    for i in range(n):
        tmpl = TEMPLATES[i % len(TEMPLATES)]
        company, industry = rng.choice(COMPANIES)
        location = rng.choice(LOCATIONS)
        title = rng.choice(tmpl["titles"])
        exp = rng.choice(tmpl["experience"])
        # slight skill jitter
        req = list(tmpl["skills_required"])
        pref = list(tmpl["skills_preferred"])
        if rng.random() < 0.3 and pref:
            # promote one preferred to required sometimes
            moved = pref.pop(rng.randrange(len(pref)))
            if moved not in req:
                req.append(moved)
        if rng.random() < 0.25:
            pref = pref[: max(1, len(pref) - 1)]
        languages = ["English"]
        if rng.random() < 0.85:
            languages.append("Arabic")
        if rng.random() < 0.35:
            languages.append("French")
        emp = rng.choice(["Full-time", "Full-time", "Internship", "Part-time", "Contract"])
        posted = today - timedelta(days=rng.randint(0, 180))
        description = tmpl["blurb"].format(location=location)
        requirements = (
            f"Requirements: {', '.join(req)}. Education: {tmpl['education']}. "
            f"Experience: {exp}. Languages: {', '.join(languages)}."
        )
        preferred = f"Preferred: {', '.join(pref)}." if pref else ""
        raw = f"{title} at {company}. {description} {requirements} {preferred}"
        jid = _job_id(f"{i}-{title}-{company}-{location}")
        jobs.append(
            {
                "job_id": jid,
                "source": "synthetic_lebanon_corpus",
                "source_url": f"https://example.local/jobs/{jid}",
                "collection_date": today.isoformat(),
                "job_title": title,
                "company": company,
                "industry": industry,
                "location": location,
                "date_posted": posted.isoformat(),
                "employment_type": emp,
                "education": tmpl["education"],
                "experience": exp,
                "languages": languages,
                "description": description,
                "requirements": requirements,
                "preferred_skills": preferred,
                "salary": None if rng.random() < 0.85 else f"${rng.randint(800, 2500)}/month",
                "raw_text": raw,
                "job_category": tmpl["category"],
                "experience_level": exp,
            }
        )
    return jobs


def main() -> None:
    root = Path(__file__).resolve().parents[2]
    raw_dir = root / "raw_data"
    proc_dir = root / "processed_data"
    raw_dir.mkdir(exist_ok=True)
    proc_dir.mkdir(exist_ok=True)
    jobs = generate_jobs(350)
    raw_path = raw_dir / "synthetic_jobs.json"
    raw_path.write_text(json.dumps(jobs, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {len(jobs)} jobs to {raw_path}")


if __name__ == "__main__":
    main()
