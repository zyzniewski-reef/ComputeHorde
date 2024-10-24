from datetime import datetime
from uuid import uuid4

import bittensor
import pytest
from compute_horde.executor_class import ExecutorClass
from compute_horde.mv_protocol.validator_requests import (
    AuthenticationPayload,
    JobFinishedReceiptPayload,
    JobStartedReceiptPayload,
    V0AuthenticateRequest,
    V0InitialJobRequest,
    V0JobAcceptedReceiptRequest,
    V0JobFinishedReceiptRequest,
)
from compute_horde.receipts.models import JobFinishedReceipt, JobStartedReceipt
from compute_horde.receipts.schemas import JobAcceptedReceiptPayload
from django.utils import timezone
from pytest_mock import MockerFixture

from compute_horde_miner.miner.models import Validator
from compute_horde_miner.miner.tests.validator import fake_validator


def _sign(msg, key: bittensor.Keypair):
    return f"0x{key.sign(msg.blob_for_signing()).hex()}"


@pytest.mark.parametrize(
    "organic_job",
    (True, False),
)
@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
async def test_receipt_is_saved(
    validator_wallet: bittensor.wallet,
    miner_wallet: bittensor.wallet,
    mocker: MockerFixture,
    organic_job: bool,
    settings,
) -> None:
    mocker.patch("compute_horde_miner.miner.miner_consumer.validator_interface.prepare_receipts")
    settings.DEBUG_TURN_AUTHENTICATION_OFF = True
    settings.BITTENSOR_WALLET = lambda: miner_wallet
    job_uuid = str(uuid4())
    await Validator.objects.acreate(
        public_key=validator_wallet.hotkey.ss58_address,
        active=True,
    )

    # 1. Authenticate to miner as test validator
    # 2. Send JobStarted and JobFinished receipts
    async with fake_validator(validator_wallet) as fake_validator_channel:
        # Authenticate, otherwise the consumer will refuse to talk to us
        auth_payload = AuthenticationPayload(
            validator_hotkey=validator_wallet.hotkey.ss58_address,
            miner_hotkey=miner_wallet.hotkey.ss58_address,
            timestamp=int(datetime.now().timestamp()),
        )
        await fake_validator_channel.send_to(
            V0AuthenticateRequest(
                payload=auth_payload,
                signature=_sign(auth_payload, validator_wallet.hotkey),
            ).model_dump_json()
        )
        response = await fake_validator_channel.receive_json_from()
        assert response == {
            "message_type": "V0ExecutorManifestRequest",
            "manifest": {
                "executor_classes": [{"executor_class": "spin_up-4min.gpu-24gb", "count": 1}],
            },
        }

        # Send the receipts
        job_started_receipt_payload = JobStartedReceiptPayload(
            job_uuid=job_uuid,
            is_organic=organic_job,
            miner_hotkey=miner_wallet.hotkey.ss58_address,
            validator_hotkey=validator_wallet.hotkey.ss58_address,
            timestamp=timezone.now(),
            executor_class=ExecutorClass.spin_up_4min__gpu_24gb,
            max_timeout=60,
            ttl=5,
        )
        job_started_receipt_signature = _sign(job_started_receipt_payload, validator_wallet.hotkey)
        await fake_validator_channel.send_to(
            V0InitialJobRequest(
                job_uuid=job_uuid,
                executor_class=ExecutorClass.spin_up_4min__gpu_24gb,
                base_docker_image_name="it's teeeeests",
                timeout_seconds=123,
                job_started_receipt_payload=job_started_receipt_payload,
                job_started_receipt_signature=job_started_receipt_signature,
            ).model_dump_json()
        )

        # skip doing the job, and only send receipts

        job_accepted_receipt_payload = JobAcceptedReceiptPayload(
            job_uuid=job_uuid,
            miner_hotkey=miner_wallet.hotkey.ss58_address,
            validator_hotkey=validator_wallet.hotkey.ss58_address,
            timestamp=timezone.now(),
            time_accepted=timezone.now(),
            ttl=5,
        )
        await fake_validator_channel.send_to(
            V0JobAcceptedReceiptRequest(
                job_uuid=job_uuid,
                payload=job_accepted_receipt_payload,
                signature=_sign(job_accepted_receipt_payload, validator_wallet.hotkey),
            ).model_dump_json()
        )

        job_finished_receipt_payload = JobFinishedReceiptPayload(
            job_uuid=job_uuid,
            miner_hotkey=miner_wallet.hotkey.ss58_address,
            validator_hotkey=validator_wallet.hotkey.ss58_address,
            timestamp=timezone.now(),
            time_started=timezone.now(),
            time_took_us=123,
            score_str="123.45",
        )
        await fake_validator_channel.send_to(
            V0JobFinishedReceiptRequest(
                job_uuid=job_uuid,
                payload=job_finished_receipt_payload,
                signature=_sign(job_finished_receipt_payload, validator_wallet.hotkey),
            ).model_dump_json()
        )

    assert await JobStartedReceipt.objects.filter(
        job_uuid=job_uuid, is_organic=organic_job
    ).aexists()
    assert await JobFinishedReceipt.objects.filter(job_uuid=job_uuid).aexists()
