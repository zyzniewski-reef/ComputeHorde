import uuid

import pytest
from compute_horde.executor_class import DEFAULT_EXECUTOR_CLASS
from compute_horde.mv_protocol.miner_requests import (
    V0DeclineJobRequest,
    V0ExecutorReadyRequest,
    V0JobFailedRequest,
    V0JobFinishedRequest,
)

from compute_horde_validator.validator.facilitator_client import OrganicJob
from compute_horde_validator.validator.miner_driver import execute_organic_job
from compute_horde_validator.validator.models import Miner

from .helpers import MockMinerClient, get_dummy_job_request, get_miner_client

WEBSOCKET_TIMEOUT = 10


@pytest.mark.asyncio
@pytest.mark.django_db(databases=["default", "default_alias"], transaction=True)
@pytest.mark.parametrize(
    "futures_result,expected_job_status_updates,organic_job_status",
    [
        ((None, None), ["failed"], OrganicJob.Status.FAILED),
        ((V0DeclineJobRequest, None), ["rejected"], OrganicJob.Status.FAILED),
        ((V0ExecutorReadyRequest, None), ["accepted", "failed"], OrganicJob.Status.FAILED),
        (
            (V0ExecutorReadyRequest, V0JobFailedRequest),
            ["accepted", "failed"],
            OrganicJob.Status.FAILED,
        ),
        (
            (V0ExecutorReadyRequest, V0JobFinishedRequest),
            ["accepted", "completed"],
            OrganicJob.Status.COMPLETED,
        ),
    ],
)
async def test_miner_driver(futures_result, expected_job_status_updates, organic_job_status):
    miner, _ = await Miner.objects.aget_or_create(hotkey="miner_client")
    job_uuid = str(uuid.uuid4())
    job_request = get_dummy_job_request(job_uuid)

    job = await OrganicJob.objects.acreate(
        job_uuid=job_uuid,
        miner=miner,
        miner_address="irrelevant",
        miner_address_ip_version=4,
        miner_port=9999,
        executor_class=DEFAULT_EXECUTOR_CLASS,
        job_description="User job from facilitator",
    )
    miner_client = get_miner_client(MockMinerClient, job_uuid)
    f0, f1 = futures_result
    if f0:
        miner_client.job_states[job_uuid].miner_ready_or_declining_future.set_result(
            f0(job_uuid=job_uuid)
        )
    if f1:
        miner_client.job_states[job_uuid].miner_finished_or_failed_future.set_result(
            f1(
                job_uuid=job_uuid,
                docker_process_stdout="mocked stdout",
                docker_process_stderr="mocked stderr",
            )
        )

    job_status_updates = []

    async def track_job_status_updates(x):
        job_status_updates.append(x)

    await execute_organic_job(
        miner_client,
        job,
        job_request,
        total_job_timeout=1,
        wait_timeout=1,
        notify_callback=track_job_status_updates,
    )

    assert len(job_status_updates) == len(expected_job_status_updates)
    for job_status, expected_status in zip(job_status_updates, expected_job_status_updates):
        assert job_status.status == expected_status
        assert job_status.uuid == job_uuid

    job = await OrganicJob.objects.aget(job_uuid=job_uuid)
    assert job.status == organic_job_status
    if organic_job_status == OrganicJob.Status.COMPLETED:
        assert job.stdout == "mocked stdout"
        assert job.stderr == "mocked stderr"
