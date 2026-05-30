from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from app.models.user import User
from app.models.contact import EmergencyContact
from app.schemas.contact import ContactCreate, ContactSchema
from app.services.auth_service import get_current_user
from app.utils.logger import Logger

router = APIRouter(prefix="/contacts", tags=["Emergency Contacts"])


def _schema(c: EmergencyContact) -> ContactSchema:
    return ContactSchema(id=c.id, name=c.name, relationship=c.relationship,
                         phoneNumber=c.phone_number, priority=c.priority)


@router.get("", response_model=List[ContactSchema])
async def get_contacts(current_user: User = Depends(get_current_user)):
    contacts = await EmergencyContact.find(EmergencyContact.user_id == current_user.id).to_list()
    return [_schema(c) for c in contacts]


@router.post("", response_model=ContactSchema, status_code=status.HTTP_201_CREATED)
async def add_contact(payload: ContactCreate, current_user: User = Depends(get_current_user)):
    count = await EmergencyContact.find(EmergencyContact.user_id == current_user.id).count()
    if count >= 3:
        raise HTTPException(status_code=400, detail="Maximum 3 emergency contacts allowed.")
    contact = EmergencyContact(
        user_id=current_user.id,
        name=payload.name,
        relationship=payload.relationship,
        phone_number=payload.phoneNumber,
        priority=payload.priority,
    )
    await contact.insert()
    Logger.info(f"Contacts: Added {contact.name} for user {current_user.id}")
    return _schema(contact)


@router.put("/{contact_id}", response_model=ContactSchema)
async def update_contact(contact_id: str, payload: ContactCreate, current_user: User = Depends(get_current_user)):
    contact = await EmergencyContact.find_one(
        EmergencyContact.id == contact_id, EmergencyContact.user_id == current_user.id
    )
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")
    contact.name = payload.name
    contact.relationship = payload.relationship
    contact.phone_number = payload.phoneNumber
    contact.priority = payload.priority
    await contact.save()
    return _schema(contact)


@router.delete("/{contact_id}")
async def delete_contact(contact_id: str, current_user: User = Depends(get_current_user)):
    contact = await EmergencyContact.find_one(
        EmergencyContact.id == contact_id, EmergencyContact.user_id == current_user.id
    )
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")
    await contact.delete()
    Logger.info(f"Contacts: Deleted {contact_id} for user {current_user.id}")
    return {"success": True}
