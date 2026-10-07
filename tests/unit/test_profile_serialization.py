from profile.serialization import dict_to_user_profile, user_profile_to_dict


def test_dict_to_user_profile_preserves_new_profile_fields():
    profile = dict_to_user_profile(
        {
            "skills": [{"Name": "Python", "Level": "high"}],
            "core_competences": ["Technical leadership"],
            "additional_informations": ["Available for relocation"],
            "work_experiences": [
                {
                    "Company": "Analytical Engines",
                    "RealisationDescription": ["Delivered a working engine"],
                }
            ],
            "education": [
                {
                    "Institution": "University",
                    "Location": "London",
                    "Degree": "BSc",
                    "Completed": True,
                }
            ],
        }
    )

    assert profile.Skills[0].Name == "Python"
    assert profile.CoreCompetences == ["Technical leadership"]
    assert profile.AdditionalInformations == ["Available for relocation"]
    assert profile.WorkExperiences[0].RealisationDescription == ["Delivered a working engine"]
    assert profile.Education[0].Location == "London"
    assert profile.Education[0].Completed is True

    serialized = user_profile_to_dict(profile)
    assert serialized["Skills"][0]["Name"] == "Python"
    assert serialized["CoreCompetences"] == ["Technical leadership"]
    assert serialized["AdditionalInformations"] == ["Available for relocation"]


def test_dict_to_user_profile_reads_legacy_technical_skills_and_education():
    profile = dict_to_user_profile(
        {
            "TechnicalSkills": [{"Name": "Python", "Level": "high"}],
            "education": [{"Institution": "University", "Degree": "BSc"}],
        }
    )

    assert profile.Skills[0].Name == "Python"
    assert profile.Education[0].Location is None
    assert profile.Education[0].Completed is None
