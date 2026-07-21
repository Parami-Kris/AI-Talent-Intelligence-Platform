# LLM judgment-quality benchmark report

Generated: 2026-07-21T16:05:43.271309+00:00
Result: 8/8 scenarios agreed with the human label

This checks the live Gemini model's actual judgment quality on education-match and experience-relevance scoring, not just the parsing/fallback code around it (see benchmarks/scenarios.py for that).

## Education match

### [AGREE] exact_degree_match

Candidate holds exactly the required degree in the required field.
- Expected status: `matched`
- LLM status: `matched`
- LLM reason: The candidate possesses a Bachelor of Science in Computer Science, which directly aligns with the job requirement.

### [AGREE] higher_degree_than_required

Candidate exceeds the requirement (Master's held, Bachelor's required) in the same field.
- Expected status: `matched`
- LLM status: `matched`
- LLM reason: An M.Sc. in Computer Science is a higher-level qualification that inherently encompasses the foundational knowledge of a Bachelor's degree in the same field.

### [AGREE] missing_degree_level

Candidate has no degree at all where a Bachelor's is required.
- Expected status: `not_matched`
- LLM status: `not_matched`
- LLM reason: The candidate has provided no educational information, failing to meet the requirement for a Bachelor's degree in Mechanical Engineering.

### [AGREE] unrelated_field

Candidate holds the required degree level but in a clearly unrelated field.
- Expected status: `not_matched`
- LLM status: `not_matched`
- LLM reason: The candidate's degree is in Fine Arts, which is not equivalent or related to the required Electrical Engineering field of study.

### [AGREE] adjacent_field_partial_credit

Candidate's field is adjacent/related but not an exact match, which should read as partial rather than a full match or a full miss.
- Expected status: `partially_matched`
- LLM status: `partially_matched`
- LLM reason: The candidate holds a Bachelor's degree, which meets the academic level, but the field of study (Statistics) is related yet distinct from the specific Data Science requirement.

## Experience relevance

### [AGREE] highly_relevant_senior_experience

Years and domain both strongly match a senior backend role - should score high.
- Expected score range: [70, 100]
- LLM score: 100
- LLM reason: The candidate demonstrates a perfect overlap with all core requirements, specifically calling out FastAPI, PostgreSQL schema design, and direct mentorship responsibilities.

### [AGREE] years_present_domain_irrelevant

Candidate has enough years but in a clearly unrelated domain (retail sales, not engineering) - relevance should score low despite meeting the years threshold.
- Expected score range: [0, 40]
- LLM score: 15
- LLM reason: The candidate has no professional machine learning or model deployment experience. Using a Python-based reporting tool in a retail management context does not constitute software engineering or ML production experience.

### [AGREE] adjacent_domain_partial_relevance

Candidate has relevant engineering experience but in an adjacent domain (data analytics, not ML engineering) - should land in the middle band, not high or low.
- Expected score range: [40, 69]
- LLM score: 45
- LLM reason: The candidate has a solid foundation in Python and statistical modeling but lacks the core engineering responsibilities required for this role, specifically production model deployment and monitoring infrastructure.
