from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.ticket_csat import TicketCsatPublicRead, TicketCsatSubmitBody
from app.services.ticket_csat import MSG_TOKEN_INVALIDO, consultar_csat_publico, registrar_csat_publico

router = APIRouter(prefix="/public/csat", tags=["public-csat"])


@router.get("/tickets/{token}", response_model=TicketCsatPublicRead)
def obter_csat_ticket(token: str, db: Session = Depends(get_db)):
    data = consultar_csat_publico(db, token)
    return TicketCsatPublicRead(**data)


@router.post("/tickets/{token}", response_model=TicketCsatPublicRead)
def enviar_csat_ticket(token: str, body: TicketCsatSubmitBody, db: Session = Depends(get_db)):
    try:
        registrar_csat_publico(db, token, nota=body.nota, comentario=body.comentario)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    data = consultar_csat_publico(db, token)
    if data.get("status") == "invalido":
        raise HTTPException(status_code=400, detail=MSG_TOKEN_INVALIDO)
    return TicketCsatPublicRead(**data)
