from candidate_profile.serialization import dict_to_user_profile, user_profile_to_dict


def test_dict_to_user_profile_preserves_new_profile_fields():
    profile = dict_to_user_profile(
        {
            "skills": [{"Name": "Python", "Level": "high"}],
            "core_competences": ["Technical leadership"],
            "additional_informations": ["Available for relocation"],
            "work_experiences": [
                {
                    "Company": "Analytical Engines",
                    "lOcAtIoN": "Montreal",
                    "rEaLiSaTiOnDeScRiPtIoN": ["Delivered a working engine"],
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
    assert profile.WorkExperiences[0].Location == "Montreal"
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


def test_dict_to_user_profile_accepts_case_insensitive_keys():
    profile = dict_to_user_profile(
        {
            "sKiLlS": [{"nAmE": "Python", "lEvEl": "Expert"}],
            "wOrK_eXpErIeNcEs": [{"cOmPaNy": "Analytical Engines", "tItLe": "Engineer"}],
            "eDuCaTiOn": [{"iNsTiTuTiOn": "University", "dEgReE": "BSc"}],
            "nAmE": "Ada Example",
        }
    )

    assert profile.Name == "Ada Example"
    assert profile.Skills[0].Name == "Python"
    assert profile.Skills[0].Level == "Expert"
    assert profile.WorkExperiences[0].Company == "Analytical Engines"
    assert profile.WorkExperiences[0].Title == "Engineer"
    assert profile.Education[0].Institution == "University"
    assert profile.Education[0].Degree == "BSc"
