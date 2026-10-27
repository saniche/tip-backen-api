PROFILE_RESPONSE = {
    "Name": "Test Candidate",
    "Email": "",
    "Phone": "",
    "Location": "",
    "LinkedIn": "",
    "Summary": "Python engineer",
    "SoftSkills": [],
    "CoreCompetences": [],
    "Languages": ["English"],
    "Certifications": [],
    "WorkExperiences": [],
    "Education": [],
    "TotalYearsOfExperience": 0,
    "PreferredJobTitles": [],
    "PreferredLocations": [],
    "Skills": [{"Name": "Python", "Level": "Intermediate"}],
    "AdditionalInformations": [],
}

JOB_RESPONSE = {
    "key_responsibilities": ["Build APIs"],
    "required": {"qualifications": [], "skills": ["Python"]},
    "desirable": {"qualifications": [], "skills": ["FastAPI"]},
    "tools_and_technologies": ["Python", "FastAPI"],
}

MATCH_RESPONSE = {
    "requirements": [
        {"criterion": "Python", "judgment": "Yes", "evidence": "The profile includes Python."}
    ],
    "desirables": [],
    "notes": "The profile was assessed against the supplied criteria.",
    "analysis": {
        "eligibility": "Mandatory requirements must be verified.",
        "matching": "The profile shows relevant evidence.",
        "chance_of_success": "Hiring outcomes remain uncertain.",
    },
}

CV_RESPONSE = {
    "target_role": "Python Engineer",
    "summary": "Python engineer tailored for the target role.",
    "experience": [],
    "education": [],
    "certifications": [],
    "skills": ["Python"],
}