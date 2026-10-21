"""Concurrent read-only preparation for the SIIR reconciliation callback.

This module has no application or database imports. Each loader callable is
submitted independently and must acquire its own connection through its own
read path; the helper never shares a connection across worker threads.
"""

from concurrent.futures import ThreadPoolExecutor, as_completed


_SERIES_KEYS = ('riego', 'cu_riego', 'drena_cu')
_METADATA_KEYS = ('wip', 'rec_curves', 'max_rec', 'ciclo_d')
_MAX_WORKERS = 4


def prepare_recon_inputs(labels, start, end, metadata_by_label,
                         series_loaders, activity_loader=None):
    """Load independent input series for one calculation window concurrently.

    Args:
        labels: material labels, typically ``('OXIDOS', 'SULFUROS')``.
        start, end: the exact bounds passed unchanged to each series loader.
        metadata_by_label: already-loaded metadata with keys ``wip``,
            ``rec_curves``, ``max_rec`` and ``ciclo_d`` for each label.
        series_loaders: mapping for ``riego``, ``cu_riego`` and ``drena_cu``;
            each callable receives ``(label, start, end)``.
        activity_loader: optional callable receiving ``label`` and returning
            the ``_fechas_actividad`` pair ``(riego_dates, drena_dates)``.

    Returns ``(materials, activity_dates)``. ``materials[label]`` has exactly
    the same keys and values as ``pad_dashboard._load_material_window``.
    Metadata is passed through without querying. If any job fails, pending
    jobs are cancelled best effort and the contextual exception propagates;
    no partial dictionaries are returned.
    """
    labels = tuple(labels)
    if len(set(labels)) != len(labels):
        raise ValueError('labels must be unique')
    missing_loaders = [key for key in _SERIES_KEYS if not callable(series_loaders.get(key))]
    if missing_loaders:
        raise ValueError('missing series loader(s): ' + ', '.join(missing_loaders))
    for label in labels:
        missing_metadata = [key for key in _METADATA_KEYS
                            if key not in metadata_by_label.get(label, {})]
        if missing_metadata:
            raise KeyError(f'{label}: missing metadata: {", ".join(missing_metadata)}')

    jobs = []
    for label in labels:
        for key in _SERIES_KEYS:
            jobs.append((label, key, series_loaders[key], (label, start, end)))
        if activity_loader is not None:
            jobs.append((label, 'activity_dates', activity_loader, (label,)))

    materials = {
        label: {key: metadata_by_label[label][key] for key in _METADATA_KEYS}
        for label in labels
    }
    activity_dates = {}
    if not jobs:
        return materials, activity_dates

    pool = ThreadPoolExecutor(max_workers=min(_MAX_WORKERS, len(jobs)))
    futures = {
        pool.submit(loader, *args): (label, key)
        for label, key, loader, args in jobs
    }
    try:
        for future in as_completed(futures):
            label, key = futures[future]
            try:
                value = future.result()
            except Exception as exc:
                for pending in futures:
                    if pending is not future:
                        pending.cancel()
                raise RuntimeError(f'failed loading {key} for {label}') from exc
            if key == 'activity_dates':
                activity_dates[label] = value
            else:
                materials[label][key] = value
    finally:
        pool.shutdown(wait=True, cancel_futures=True)

    return materials, activity_dates
