from fastapi import APIRouter, Depends, HTTPException, status
from app.models.user import User
from app.schemas.auth import RegisterRequest, LoginRequest, TokenResponse
from app.schemas.profile import ProfileSchema
from app.services.auth_service import create_access_token, get_current_user
from app.utils.logger import Logger

router = APIRouter(prefix="/auth", tags=["Authentication"])


def _to_profile(user: User) -> ProfileSchema:
    s = user.settings
    return ProfileSchema(
        fullName=user.full_name,
        age=user.age,
        dateOfBirth=user.date_of_birth,
        gender=user.gender,
        bloodGroup=user.blood_group,
        medicalNotes=user.medical_notes,
        phone=user.phone,
        preferredLanguage=user.preferred_language,
        notificationEnabled=s.notification_enabled,
        privacyEnabled=s.privacy_enabled,
        themeDarkMode=s.theme_dark_mode,
        sosSensitivity=s.sos_sensitivity,
    )


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(payload: RegisterRequest):
    """
    Register a new user. Returns a JWT token and full profile on success.
    Phone number must be unique — returns 400 if already registered.
    """
    existing = await User.find_one(User.phone == payload.phone)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This phone number is already registered. Please log in instead.",
        )

    user = User(
        phone=payload.phone,
        full_name=payload.full_name,
        age=payload.age or "",
        date_of_birth=payload.date_of_birth or "",
        gender=payload.gender or "",
        blood_group=payload.blood_group or "",
        medical_notes=payload.medical_notes or "",
        preferred_language=payload.preferred_language or "English",
    )
    await user.insert()
    Logger.info(f"Auth: Registered new user {user.id} — phone {payload.phone}")

    token = create_access_token(data={"sub": user.phone})
    return TokenResponse(success=True, token=token, user=_to_profile(user))


@router.post("/login", response_model=TokenResponse)
async def login(payload: LoginRequest):
    """
    Log in with a registered phone number. Returns JWT token and profile.
    """
    user = await User.find_one(User.phone == payload.phone)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Phone number not registered. Please register first.",
        )

    token = create_access_token(data={"sub": user.phone})
    Logger.info(f"Auth: Login successful for user {user.id}")
    return TokenResponse(success=True, token=token, user=_to_profile(user))


@router.post("/logout")
async def logout(_current_user: User = Depends(get_current_user)):
    """Invalidate session (client should discard the JWT token)."""
    return {"success": True, "message": "Logged out successfully"}


@router.get("/me", response_model=ProfileSchema)
async def get_me(current_user: User = Depends(get_current_user)):
    """Get the authenticated user's profile."""
    return _to_profile(current_user)
