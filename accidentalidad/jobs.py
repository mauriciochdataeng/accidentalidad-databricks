"""Despliegue de la definición completa sin ejecutar ni duplicar Jobs."""


def deploy_job(client, name, settings):
    matching = [job for job in client.jobs.list(name=name)
                if job.settings and job.settings.name == name]
    if len(matching) > 1:
        raise ValueError(f"Hay varios Jobs llamados {name}; resuelva la ambigüedad")
    if not matching:
        return client.jobs.create(**settings.as_shallow_dict()).job_id
    job_id = matching[0].job_id
    if next(iter(client.jobs.list_runs(job_id=job_id, active_only=True, limit=1)), None) is not None:
        raise RuntimeError("Hay una ejecución activa; despliegue de nuevo cuando termine")
    client.jobs.reset(job_id=job_id, new_settings=settings)
    return job_id
