PROFILE_RESPONSE = {
    "Name": "Test Candidate",
    "Email": "",
    "Phone": "",
    "Location": "",
    "LinkedIn": "",
    "Summary": "Python engineer",
    "SoftSkills": [],
    "Languages": ["English"],
    "Certifications": [],
    "WorkExperiences": [],
    "Education": [],
    "TotalYearsOfExperience": 0,
    "PreferredJobTitles": [],
    "PreferredLocations": [],
    "TechnicalSkills": [{"Name": "Python", "Level": "medium"}],
}

JOB_RESPONSE = {
    "key_responsibilities": ["Build APIs"],
    "required": {"qualifications": [], "skills": ["Python"]},
    "desirable": {"qualifications": [], "skills": ["FastAPI"]},
    "technical_stack": ["Python", "FastAPI"],
}

MATCH_RESPONSE = {
    "required_qualifications": [],
    "required_skills": [{"result": "Yes", "value": "Python", "rationale": "Profile contains Python."}],
    "desirable_qualifications": [],
    "desirable_skills": [],
    "technical_stack": [{"result": "Yes", "value": "Python", "rationale": "Profile contains Python."}],
    "notes": "Validated profile-to-job comparison.",
}

CV_RESPONSE = {
    "target_role": "Python Engineer",
    "summary": "Python engineer tailored for the target role.",
    "experience": [],
    "education": [],
    "certifications": [],
    "skills": ["Python"],
}