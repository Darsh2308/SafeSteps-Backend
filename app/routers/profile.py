from fastapi import APIRouter, Depends
from app.models.user import User
from app.schemas.profile import ProfileSchema, ProfileUpdate, LanguageUpdate, SimUpdate, SettingsSchema
from app.services.auth_service import get_current_user
from app.utils.logger import Logger

router = APIRouter(prefix="/profile", tags=["Profile Management"])


def _profile(user: User) -> ProfileSchema:
    s = user.settings
    return ProfileSchema(
        fullName=user.full_name, age=user.age, dateOfBirth=user.date_of_birth,
        gender=user.gender, bloodGroup=user.blood_group, medicalNotes=user.medical_notes,
        phone=user.phone, preferredLanguage=user.preferred_language,
        notificationEnabled=s.notification_enabled, privacyEnabled=s.privacy_enabled,
        themeDarkMode=s.theme_dark_mode, sosSensitivity=s.sos_sensitivity,
    )


@router.get("", response_model=ProfileSchema)
async def get_profile(current_user: User = Depends(get_current_user)):
    return _profile(current_user)


@router.put("", response_model=ProfileSchema)
async def update_profile(payload: ProfileUpdate, current_user: User = Depends(get_current_user)):
    u = current_user
    for field, attr in [("fullName", "full_name"), ("age", "age"), ("dateOfBirth", "date_of_birth"),
                        ("gender", "gender"), ("bloodGroup", "blood_group"),
                        ("medicalNotes", "medical_notes"), ("preferredLanguage", "preferred_language")]:
        val = getattr(payload, field, None)
        if val is not None:
            setattr(u, attr, val)
    for field, attr in [("notificationEnabled", "notification_enabled"), ("privacyEnabled", "privacy_enabled"),
                        ("themeDarkMode", "theme_dark_mode"), ("sosSensitivity", "sos_sensitivity")]:
        val = getattr(payload, field, None)
        if val is not None:
            setattr(u.settings, attr, val)
    await u.save()
    return _profile(u)


@router.put("/language", response_model=ProfileSchema)
async def update_language(payload: LanguageUpdate, current_user: User = Depends(get_current_user)):
    current_user.preferred_language = payload.language
    await current_user.save()
    Logger.info(f"Profile: language → {payload.language} for {current_user.id}")
    return _profile(current_user)


@router.put("/sim", response_model=ProfileSchema)
async def update_sim(payload: SimUpdate, current_user: User = Depends(get_current_user)):
    Logger.info(f"Profile: SIM slot {payload.simId} ({payload.carrier}) for {current_user.id}")
    return _profile(current_user)


@router.get("/settings", response_model=SettingsSchema)
async def get_settings(current_user: User = Depends(get_current_user)):
    s = current_user.settings
    return SettingsSchema(
        notificationEnabled=s.notification_enabled, privacyEnabled=s.privacy_enabled,
        themeDarkMode=s.theme_dark_mode, sosSensitivity=s.sos_sensitivity,
    )


@router.put("/settings", response_model=SettingsSchema)
async def update_settings(payload: SettingsSchema, current_user: User = Depends(get_current_user)):
    s = current_user.settings
    s.notification_enabled = payload.notificationEnabled
    s.privacy_enabled = payload.privacyEnabled
    s.theme_dark_mode = payload.themeDarkMode
    s.sos_sensitivity = payload.sosSensitivity
    await current_user.save()
    return SettingsSchema(
        notificationEnabled=s.notification_enabled, privacyEnabled=s.privacy_enabled,
        themeDarkMode=s.theme_dark_mode, sosSensitivity=s.sos_sensitivity,
    )
