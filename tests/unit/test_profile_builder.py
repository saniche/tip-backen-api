import pytest

import pipeline.profile_builder as profile_builder


@pytest.mark.asyncio
async def test_extract_profile_converts_typed_structured_output(monkeypatch):
    async def fake_call(*args, **kwargs):
        schema = args[2]
        return schema(
            Name="Ada", Email="", Phone="", Location="Ottawa", LinkedIn="", Summary="Engineer",
            SoftSkills=[], Languages=["French"], Certifications=[], WorkExperiences=[], Education=[],
            TotalYearsOfExperience=5, PreferredJobTitles=[], PreferredLocations=[],
            TechnicalSkills=[{"Name": "Python", "Level": "high"}],
        )

    monkeypatch.setattr(profile_builder, "call_openai_structured", fake_call)
    profile = await profile_builder.extract_profile({"content": "Ada develops Python systems."})

    assert profile.Name == "Ada"
    assert profile.TechnicalSkills[0].Name == "Python"
    assert profile.TotalYearsOfExperience == 5