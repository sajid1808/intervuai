from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User, Profile
from app.schemas.auth import UserRegister, UserLogin, Token, UserResponse, ProfileUpdate, ProfileResponse
from app.security import get_password_hash, verify_password, create_access_token, get_current_user

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(user_data: UserRegister, db: Session = Depends(get_db)):
    # Check if user already exists
    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email is already registered"
        )
    
    # Hash password and create User
    hashed_pwd = get_password_hash(user_data.password)
    # Check if this is the very first user; if so, make them an admin
    total_users = db.query(User).count()
    is_admin = True if total_users == 0 else False
    
    new_user = User(
        email=user_data.email,
        password_hash=hashed_pwd,
        is_admin=is_admin
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    # Create Profile linked to User
    new_profile = Profile(
        user_id=new_user.id,
        full_name=user_data.full_name,
        skills=[],
        preferred_roles=[]
    )
    db.add(new_profile)
    db.commit()
    db.refresh(new_user)
    
    return new_user

@router.post("/login", response_model=Token)
def login(login_data: UserLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == login_data.email).first()
    if not user or not verify_password(login_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token = create_access_token(data={"sub": user.email})
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "is_admin": user.is_admin,
        "email": user.email
    }

@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    return current_user

@router.get("/profile", response_model=ProfileResponse)
def get_profile(current_user: User = Depends(get_current_user)):
    if not current_user.profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found"
        )
    # Set properties for serialization
    profile = current_user.profile
    return {
        "id": profile.id,
        "user_id": profile.user_id,
        "full_name": profile.full_name,
        "education": profile.education,
        "skills": profile.skills,
        "experience_level": profile.experience_level,
        "preferred_roles": profile.preferred_roles,
        "created_at": profile.created_at,
        "updated_at": profile.updated_at
    }

@router.put("/profile", response_model=ProfileResponse)
def update_profile(
    profile_data: ProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    profile = current_user.profile
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found"
        )
        
    if profile_data.full_name is not None:
        profile.full_name = profile_data.full_name
    if profile_data.education is not None:
        profile.education = profile_data.education
    if profile_data.skills is not None:
        profile.skills = profile_data.skills
    if profile_data.preferred_roles is not None:
        profile.preferred_roles = profile_data.preferred_roles
    if profile_data.experience_level is not None:
        profile.experience_level = profile_data.experience_level
        
    db.commit()
    db.refresh(profile)
    
    return {
        "id": profile.id,
        "user_id": profile.user_id,
        "full_name": profile.full_name,
        "education": profile.education,
        "skills": profile.skills,
        "experience_level": profile.experience_level,
        "preferred_roles": profile.preferred_roles,
        "created_at": profile.created_at,
        "updated_at": profile.updated_at
    }
