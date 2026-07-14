from backend.app.services.job_search_service import expand_query

COMMON_CS_JOB_TITLES = [
    "Software Engineer",
    "Software Developer",
    "Backend Developer",
    "Frontend Developer",
    "Full Stack Developer",
    "Data Scientist",
    "Data Engineer",
    "Data Analyst",
    "Machine Learning Engineer",
    "AI Engineer",
    "DevOps Engineer",
    "Cloud Engineer",
    "Site Reliability Engineer",
    "QA Engineer",
    "Mobile Developer",
    "iOS Developer",
    "Android Developer",
    "Product Manager",
    "Cybersecurity Engineer",
    "Systems Engineer",
    "Database Administrator",
    "Network Engineer",
    "UI/UX Designer",
    "Business Analyst",
    "Solutions Architect",
]


def main():
    for title in COMMON_CS_JOB_TITLES:
        related = expand_query(title)
        print(f"{title!r} -> {related}")

    print(f"\nSeeded {len(COMMON_CS_JOB_TITLES)} common CS/tech job titles.")


if __name__ == "__main__":
    main()
