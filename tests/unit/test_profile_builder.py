import pytest

import profile.profile_builder as profile_builder


@pytest.mark.asyncio
async def test_extract_profile_converts_typed_structured_output(monkeypatch):
    captured = {}

    async def fake_call(*args, **kwargs):
        captured.update({"system": args[0], "content": args[1]})
        schema = args[2]
        return schema(
            Name="Ada", Email="", Phone="", Location="Ottawa", LinkedIn="", Summary="Engineer",
            SoftSkills=[], CoreCompetences=["Leadership"], Languages=["French"], Certifications=[],
            WorkExperiences=[{
                "Company": "Analytical Engines",
                "Title": "Engineer",
                "StartDate": "1840",
                "EndDate": "1843",
                "Summary": "Built analytical systems",
                "RealisationDescription": ["Delivered a working engine"],
            }],
            Education=[{
                "Institution": "University",
                "Location": "Ottawa",
                "Degree": "MSc",
                "Field": "Mathematics",
                "Year": "1840",
                "Completed": True,
            }],
            TotalYearsOfExperience=5, PreferredJobTitles=[], PreferredLocations=[],
            Skills=[
                {"Name": "Python", "Level": "Intermediate"},
                {"Name": "Architecture", "Level": "Expert"},
                {"Name": "API design", "Level": "Advanced"},
                {"Name": "Scripting", "Level": "Beginner"},
            ],
            AdditionalInformations=["Available for relocation"],
        )

    monkeypatch.setattr(profile_builder, "call_openai_structured", fake_call)
    profile = await profile_builder.extract_profile(
        {"content": "Ada develops Python systems."},
        output_language="French",
    )

    assert profile.Name == "Ada"
    assert [(skill.Name, skill.Level) for skill in profile.Skills] == [
        ("Architecture", "Expert"),
        ("API design", "Advanced"),
        ("Python", "Intermediate"),
        ("Scripting", "Beginner"),
    ]
    assert profile.TotalYearsOfExperience == 5
    assert profile.CoreCompetences == ["Leadership"]
    assert profile.AdditionalInformations == ["Available for relocation"]
    assert profile.WorkExperiences[0].RealisationDescription == ["Delivered a working engine"]
    assert profile.Education[0].Location == "Ottawa"
    assert profile.Education[0].Completed is True
    assert "in French" in captured["system"]
    assert "only explicitly stated" in captured["system"]
    assert "Omit a skill when the source does not support a level" in captured["system"]