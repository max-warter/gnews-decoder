from typing import List, Optional
from fastapi import FastAPI, HTTPException
from fastapi.concurrency import run_in_threadpool
from googlenewsdecoder import gnewsdecoder
from pydantic import BaseModel

app = FastAPI(
    title="Google News URL Decoder Service",
    description="Microservice basant le décodage sur la bibliothèque googlenewsdecoder",
    version="1.0.0",
)


# Modèles de validation des données
class ItemRequest(BaseModel):
    url: str
    msg_index: Optional[int] = None


class BatchRequest(BaseModel):
    items: List[ItemRequest]


class DecodeResult(BaseModel):
    url: str
    decoded_url: str
    status: bool
    msg_index: Optional[int] = None


def run_decoder(target_url: str) -> str:
    """Fonction synchrone qui appelle googlenewsdecoder."""
    try:
        # Appel à la bibliothèque demandée
        res = gnewsdecoder(target_url, interval=1)
        if isinstance(res, dict) and res.get("status"):
            return res.get("decoded_url", target_url)
        return target_url
    except Exception:
        return target_url


@app.get("/")
def health_check():
    return {"status": "ok", "message": "Service actif avec googlenewsdecoder"}


@app.post("/decode", response_model=DecodeResult)
async def decode_single_url(payload: ItemRequest):
    """Décode une seule URL."""
    if not payload.url:
        raise HTTPException(status_code=400, detail="L'URL est requise.")

    # Exécution dans un threadpool pour ne pas bloquer la boucle d'événements FastAPI
    decoded = await run_in_threadpool(run_decoder, payload.url)
    is_success = decoded != payload.url

    return DecodeResult(
        url=payload.url,
        decoded_url=decoded,
        status=is_success,
        msg_index=payload.msg_index,
    )


@app.post("/decode-batch", response_model=List[DecodeResult])
async def decode_batch_urls(payload: BatchRequest):
    """Décode une liste d'URLs transmises en une seule requête."""
    results = []
    for item in payload.items:
        decoded = await run_in_threadpool(run_decoder, item.url)
        is_success = decoded != item.url

        results.append(
            DecodeResult(
                url=item.url,
                decoded_url=decoded,
                status=is_success,
                msg_index=item.msg_index,
            )
        )
    return results