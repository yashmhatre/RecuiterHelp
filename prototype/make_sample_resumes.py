"""Generate the synthetic sample resumes used for demoing.

Committed so a clean clone can produce them without hunting for real files. No real people:
every name, address and phone number here is invented.

    python prototype/make_sample_resumes.py
"""

from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

OUT = Path(__file__).resolve().parent / "sample_resumes"

PEOPLE: dict[str, list[str]] = {
    "Asha_Menon": [
        "Asha Menon",
        "asha.menon@example.com  |  +91 98765 43210  |  Pune, India",
        "",
        "SUMMARY",
        "Senior Python Engineer with 7 years of experience building payment systems",
        "and REST APIs. Strong on Django, PostgreSQL and AWS.",
        "",
        "SKILLS",
        "Python, Django, FastAPI, PostgreSQL, Redis, Celery, Docker, AWS, Git",
        "",
        "EXPERIENCE",
        "Lead Engineer, Payments Platform (2021-present)",
        "   Built and scaled a Django payments service on AWS.",
        "",
        "Backend Engineer, Retail Tech (2018-2021)",
        "   REST APIs with Django and PostgreSQL.",
        "",
        "Notice period: 30 days",
    ],
    "Rohit_Nair": [
        "Rohit Nair",
        "rohit.nair@example.com  |  +91 99887 66554  |  Bangalore, India",
        "",
        "SUMMARY",
        "Java Backend Developer with 5 years of experience on Spring Boot",
        "microservices and MySQL.",
        "",
        "SKILLS",
        "Java, Spring Boot, Hibernate, MySQL, Kafka, Docker, Kubernetes, Maven",
        "",
        "EXPERIENCE",
        "Senior Developer, Logistics Co (2020-present)",
        "   Spring Boot services handling order routing.",
        "",
        "Notice period: 60 days",
    ],
    "Meera_Iyer": [
        "Meera Iyer",
        "meera.iyer@example.com  |  +91 91234 56789  |  Pune, India",
        "",
        "SUMMARY",
        "Data Engineer with 6 years of experience building batch and streaming",
        "pipelines on Spark and Airflow.",
        "",
        "SKILLS",
        "Python, Spark, Airflow, SQL, Snowflake, dbt, Kafka, AWS, Pandas",
        "",
        "EXPERIENCE",
        "Data Engineer, Analytics Team (2019-present)",
        "   Airflow DAGs and Spark jobs over a Snowflake warehouse.",
        "",
        "Notice period: 45 days",
    ],
    "Karan_Shah": [
        "Karan Shah",
        "karan.shah@example.com  |  +91 90011 22334  |  Remote",
        "",
        "SUMMARY",
        "Full Stack Engineer with 4 years of experience on React front ends and",
        "FastAPI back ends.",
        "",
        "SKILLS",
        "TypeScript, React, Next.js, Python, FastAPI, PostgreSQL, Docker, AWS",
        "",
        "EXPERIENCE",
        "Full Stack Engineer, SaaS Startup (2021-present)",
        "   React and FastAPI product work end to end.",
        "",
        "Notice period: Immediate",
    ],
}


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for stem, lines in PEOPLE.items():
        path = OUT / f"{stem}.pdf"
        page = canvas.Canvas(str(path), pagesize=A4)
        y = 800
        for line in lines:
            page.setFont("Helvetica-Bold" if line and line.isupper() else "Helvetica", 11)
            page.drawString(60, y, line)
            y -= 18
        page.save()
        print(f"wrote {path}")


if __name__ == "__main__":
    main()
