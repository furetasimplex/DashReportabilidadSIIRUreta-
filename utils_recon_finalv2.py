"""Reconciliación de masa y cobre con topología por ejecución (sin estado global mutable)."""
import numpy as np
import pandas as pd
from time import perf_counter
from reconciliation.topology import reference_model6
from reconciliation.mass_constraints import mass_flow_rules, MASS_COMPARISON_TOL

# Compatibility for external imports. Application callbacks pass database topology.
nombres_flujos = list(reference_model6().flow_names)
nodos_names = list(reference_model6().node_names)


def get_topology_matrix(topology=None):
    topology = topology or reference_model6()
    return topology.matrix.copy(), topology.deltas.copy()


def validate_inputs(measurements, error, topology):
    values = np.asarray(measurements, dtype=float)
    tolerances = np.asarray(error, dtype=float)
    expected = (len(topology.codes), 2)
    if values.shape != expected or tolerances.shape != expected:
        raise ValueError(f'El modelo {topology.model_id} requiere mediciones y tolerancias de tamaño {expected}.')
    if not np.isfinite(values).all() or not np.isfinite(tolerances).all():
        raise ValueError('Mediciones o tolerancias faltantes/no finitas.')
    if (tolerances < 0).any():
        raise ValueError('Tolerancias negativas.')
    ordinary = np.ones(len(values), dtype=bool)
    ordinary[topology.deltas] = False
    if (values[ordinary, 0] < 0).any():
        raise ValueError('Solo los inventarios pueden tener masa negativa. Revisar: ' + ', '.join(
            topology.codes[j] for j in np.flatnonzero(ordinary & (values[:, 0] < 0))))
    ordinary_grade = np.ones(len(values), dtype=bool)
    ordinary_grade[topology.inventory_grade_indices] = False
    invalid_grade = ordinary_grade & ((values[:, 1] < 0) | (values[:, 1] > 1))
    if invalid_grade.any():
        raise ValueError('La ley de los flujos no inventario debe estar entre 0 y 100%. Revisar: '
                         + ', '.join(topology.codes[j] for j in np.flatnonzero(invalid_grade)))


def _model125_transfer_rules(topology):
    """Return exact Cu-transfer equalities only for the complete 125-flow catalog.

    The topology provider exposes the database model id and flow codes. For
    the verified application catalog, model_id=2 plus the complete F1..F125
    set is the activation signature; legacy model 6 and reduced catalogs are
    deliberately excluded.
    """
    codes = tuple(str(code).strip().upper() for code in topology.codes)
    expected = {f'F{i}' for i in range(1, 126)}
    # The active Case10013 run identifies hidrometalurgia_125_v2 as database
    # model_id=2.  Code count alone is insufficient: model 6 has had evolving
    # catalogs too, and must never inherit these model-125 definitions.
    if (getattr(topology, 'model_id', None) != 2
            or len(codes) != 125 or set(codes) != expected):
        return ()
    positions = {code: i for i, code in enumerate(codes)}
    definitions = (
        ('F25', {'F25': 1.0, 'F44': -1.0, 'F70': 1.0, 'F60': 1.0, 'F81': 1.0}),
        ('F29', {'F29': 1.0, 'F47': -1.0, 'F48': -1.0, 'F49': -1.0,
                 'F72': 1.0, 'F66': 1.0}),
    )
    rules = []
    delta_indices = set(np.asarray(topology.deltas, dtype=int).tolist())
    for name, terms in definitions:
        coefficients = np.zeros(len(codes), dtype=float)
        for code, coefficient in terms.items():
            if code not in positions:
                raise ValueError(f'Topología de 125 flujos sin {code}; no se puede aplicar {name}.')
            idx = positions[code]
            if idx in delta_indices:
                raise ValueError(f'{code} está definido como inventario delta; no se puede aplicar {name}.')
            coefficients[idx] = coefficient
        rules.append((name, coefficients))
    return tuple(rules)


def _transfer_rule_is_implied(coefficients, topology):
    """Whether an exact nodal Cu closure already implies this transfer rule."""
    rows = np.asarray(topology.balance_rows, dtype=bool)
    matrix = np.asarray(topology.matrix, dtype=float)[rows]
    if matrix.size == 0:
        return False
    before = np.linalg.matrix_rank(matrix)
    after = np.linalg.matrix_rank(np.vstack([matrix, coefficients]))
    return after == before


def desbalances(mediciones_input, error, fn="Normal", topology=None):
    topology = topology or reference_model6()
    nodos_names = list(topology.node_names)
    nombres_flujos = list(topology.flow_names)
    validate_inputs(mediciones_input, error, topology)
    # Make a copy to avoid mutating the original dataframe/array
    mediciones = np.array(mediciones_input, dtype=float, copy=True)
    error = pd.DataFrame(error).reset_index(drop=True)
    
    matriz_final, deltas = get_topology_matrix(topology)

    # Ajuste de signos por Deltas
    valid_deltas = [k for k in deltas if k < matriz_final.shape[1]]
    for k in valid_deltas:
        bool_values = matriz_final[:, k] != 0
        if k < len(mediciones):
            matriz_final[bool_values, k] = (-1 if mediciones[k, 0] >= 0 else 1)

    mediciones_calc = mediciones

    vector_masa_abs = np.abs(mediciones_calc[:, 0])
    
    # Ax (Masa)
    b_masa_ini = np.dot(matriz_final, vector_masa_abs)

    # Ax (Finos)
    b_fino_ini_Cu = np.dot(matriz_final, vector_masa_abs * mediciones_calc[:, 1])

    # Inputs por nodo (solo contribuciones positivas de la matriz)
    inputs_masa = np.dot(np.maximum(0, matriz_final), vector_masa_abs)
    inputs_fino = np.dot(np.maximum(0, matriz_final), vector_masa_abs * mediciones_calc[:, 1])
    
    pct_masa = np.divide(b_masa_ini * 100, inputs_masa, out=np.full_like(b_masa_ini, np.nan), where=(np.abs(inputs_masa) > 0))
    pct_fino = np.divide(b_fino_ini_Cu * 100, inputs_fino, out=np.full_like(b_fino_ini_Cu, np.nan), where=(np.abs(inputs_fino) > 0))

    masa_df = pd.DataFrame(nodos_names, columns=["Nodo"])
    len_min = min(len(masa_df), len(b_masa_ini))

    masa_df["Desbalance masa inicial"] = 0.0
    masa_df.loc[:len_min-1, "Desbalance masa inicial"] = b_masa_ini[:len_min]

    masa_df["Desbalance masa"] = 0.0

    masa_df["Desbalance fino inicial Cu"] = 0.0
    masa_df.loc[:len_min-1, "Desbalance fino inicial Cu"] = b_fino_ini_Cu[:len_min]

    masa_df["Desbalance fino Cu"] = 0.0

    masa_df["% Desbalance masa"] = np.nan
    masa_df.loc[:len_min-1, "% Desbalance masa"] = pct_masa[:len_min]

    masa_df["% Desbalance fino Cu"] = np.nan
    masa_df.loc[:len_min-1, "% Desbalance fino Cu"] = pct_fino[:len_min]

    return pd.DataFrame(), masa_df, pd.DataFrame(nodos_names)


def balance_core(mediciones_input, error, fn="Normal", u=1, cf=1, cw=1, expk=1, cp=1, eps=0.05, c_factor=4.0, topology=None, max_iter=50, solver_verbose=False, closure_mass=0.0, closure_copper=0.0):
    started = perf_counter()
    if isinstance(max_iter, bool) or not isinstance(max_iter, int) or max_iter <= 0:
        raise ValueError("max_iter debe ser un entero positivo.")
    topology = topology or reference_model6()
    nodos_names = list(topology.node_names)
    nombres_flujos = list(topology.flow_names)
    if not all(np.isfinite(v) and v >= 0 for v in (closure_mass, closure_copper)):
        raise ValueError("Los residuos permitidos deben ser finitos y no negativos.")
    if solver_verbose:
        print(f"Cierre permitido por nodo: masa ±{closure_mass} t; cobre ±{closure_copper} t.")
    validate_inputs(mediciones_input, error, topology)
    # Make a safe copy to prevent mutating the original input object
    mediciones = np.array(mediciones_input, dtype=float, copy=True)
    error = pd.DataFrame(error).reset_index(drop=True)

    matriz, deltas = get_topology_matrix(topology)
    transfer_rules = _model125_transfer_rules(topology)
    if transfer_rules:
        positions = {str(code).strip().upper(): i for i, code in enumerate(topology.codes)}
        for flow_code in ('F25', 'F29'):
            measured_grade = float(mediciones[positions[flow_code], 1])
            if not np.isclose(measured_grade, 1.0, rtol=0.0, atol=1e-8):
                raise ValueError(
                    f'{flow_code} en modelo 125 debe tener ley Cu 100% '
                    f'(fracción 1.0); se recibió {measured_grade:.8g}.')

    for k in deltas:
        bool_values = matriz[:, k] != 0
        matriz[bool_values, k] = (-1 if mediciones[k, 0] >= 0 else 1)
        
    inventarios_masa = 2 * (mediciones[:, 0] >= 0) - 1
    mediciones[:, 0] = np.abs(mediciones[:, 0])
    mass_rules = mass_flow_rules(topology, inventarios_masa)
    
    from gekko import GEKKO
    m = GEKKO(remote=False)
    n_components = 1
    x = m.Array(m.Var, (matriz.shape[1]))
    x_c = m.Array(m.Var, (matriz.shape[1], n_components))
    tms_medicion = mediciones[:, 0]

    mediciones_leyes = []
    for k in range(n_components):
        leyes_medicion = mediciones[:, k+1]
        mediciones_leyes.append(leyes_medicion)

    # Build only actual connections of internal nodes. A dense symbolic dot
    # retains zero * variable terms in the APMonitor model and its derivatives.
    row_flows = {i: np.flatnonzero(matriz[i]) for i in np.flatnonzero(topology.balance_rows)
                 if np.any(matriz[i])}
    balance_TMS = {i: sum(float(matriz[i, j]) * x[j] for j in indices)
                   for i, indices in row_flows.items()}
    balances = []
    for k in range(n_components):
        productos = [x[j] * x_c[j, k] for j in range(matriz.shape[1])]
        balances.append({i: sum(float(matriz[i, j]) * productos[j] for j in indices)
                         for i, indices in row_flows.items()})

    # --- NUEVAS FUNCIONES OBJETIVO ROBUSTAS ---
    def robust_obj(r):
        if fn == "Normal":
            return r**2
        elif fn == "Cauchy":
            return (cp**2) * m.log(1 + (r/cp)**2)
        elif fn == "Fair":
            abs_r = m.sqrt(r**2 + 1e-6) 
            return (cf**2) * (abs_r/cf - m.log(1 + abs_r/cf))
        elif fn == "Welsch":
            return (cw**2) * (1 - m.exp(-(r/cw)**2))
        elif fn == "Pseudo-Huber":
            return (u**2) * (m.sqrt(1 + (r/u)**2) - 1)
        elif fn == "Power":
            return (r**2)**(expk/2)
        elif fn == "Contaminated Gaussian":
            return -m.log((1-eps)*m.exp(-r**2/2) + eps*m.exp(-r**2/(2*c_factor**2)))
        else:
            return r**2 

    # One m.Obj() call per term avoids the APM 15000-char string limit
    # that occurs when complex functions (log, exp, sqrt) are accumulated
    # into a single symbolic expression across 128+ flows.
    for i in range(mediciones.shape[0]):
        if tms_medicion[i] == 0 or error.iloc[i, 0] == 0:
            continue  # Fixed variable: its objective contribution is constant.
        if tms_medicion[i] == 0:
            divisor = 1
        else:
            if error.iloc[i, 0] == 0:
                divisor = 1
            else:
                divisor = max(tms_medicion[i] * error.iloc[i, 0], 1e-6)
        r = (x[i] - tms_medicion[i]) / divisor
        m.Obj(robust_obj(r))

    for k in range(n_components):
        for i in range(mediciones.shape[0]):
            if (error.iloc[i, k+1] == 0 or mediciones_leyes[k][i] == 0
                    or tms_medicion[i] == 0):
                continue
            if mediciones_leyes[k][i] == 0:
                divisor = 1
            else:
                if error.iloc[i, k+1] == 0:
                    divisor = 1
                else:
                    divisor = max(abs(mediciones_leyes[k][i]) * error.iloc[i, k+1], 1e-6)
            r = (x_c[i, k] - mediciones_leyes[k][i]) / divisor
            m.Obj(robust_obj(r))
    m.options.SOLVER = 3
    m.options.IMODE = 3

    for i, xi in enumerate(x):
        if error.iloc[i, 0] == 0:
            x[i].lower = tms_medicion[i]
            x[i].upper = tms_medicion[i]
            x[i].value = tms_medicion[i]
        elif tms_medicion[i] == 0:
            x[i].lower = tms_medicion[i]
            x[i].upper = tms_medicion[i]
            x[i].value = tms_medicion[i]
        else:
            x[i].value = tms_medicion[i]
            x[i].lower = 0
            x[i].upper = 5e9
    N_SIGMA = 20
    for k in range(n_components):
        for i, xi in enumerate(x_c):
            if error.iloc[i, k+1] == 0:
                  x_c[i, k].lower = mediciones_leyes[k][i]
                  x_c[i, k].upper = mediciones_leyes[k][i]
                  x_c[i, k].value = mediciones_leyes[k][i]
            elif mediciones_leyes[k][i] == 0:
                  x_c[i, k].lower = 0
                  x_c[i, k].upper = 0
                  x_c[i, k].value = 0
            elif tms_medicion[i] == 0:
                  # mass is pinned at 0 → fine = mass × grade = 0 regardless of grade
                  # grade is disconnected from all constraints → pin it to avoid structural singularity
                  x_c[i, k].lower = mediciones_leyes[k][i]
                  x_c[i, k].upper = mediciones_leyes[k][i]
                  x_c[i, k].value = mediciones_leyes[k][i]
            elif i in topology.inventory_grade_indices:
                  x_c[i, k].lower = -100
                  x_c[i, k].upper = 100
                  x_c[i, k].value = mediciones_leyes[k][i]
            else:
                  x_c[i, k].value = mediciones_leyes[k][i]
                  tol_g = error.iloc[i, k+1]
                  x_c[i, k].lower = max(0.0, mediciones_leyes[k][i] * (1.0 - N_SIGMA * tol_g))
                  x_c[i, k].upper = min(1.0, mediciones_leyes[k][i] * (1.0 + N_SIGMA * tol_g))

    # In model 125, F25 and F29 are defined as transferred Cu quantities
    # (the run stores fino Cu equal to mass); represent that identity as 100%
    # Cu in the mass×grade formulation. Other flow grades remain reconciled
    # under their existing bounds and objective.
    if transfer_rules:
        positions = {str(code).strip().upper(): i for i, code in enumerate(topology.codes)}
        for flow_code in ('F25', 'F29'):
            idx = positions[flow_code]
            x_c[idx, 0].lower = 1.0
            x_c[idx, 0].upper = 1.0
            x_c[idx, 0].value = 1.0

                  
    from reconciliation.feasible_start import feasible_start
    feasibility_started = perf_counter()
    initial, feasibility_message = feasible_start(
        matriz[topology.balance_rows], tms_medicion, mediciones[:, 1],
        [(v.lower, v.upper) for v in x],
        [(x_c[i, 0].lower, x_c[i, 0].upper) for i in range(len(x))],
        closure_mass, closure_copper,
        mass_constraints=[(coefficients, gap) for _, coefficients, gap in mass_rules])
    feasibility_seconds = perf_counter() - feasibility_started
    if solver_verbose:
        print(f'Factibilidad inicial de balances nodales (masa/Cu): {feasibility_message}')
        if transfer_rules:
            print('Transferencias F25/F29 se imponen y validan en solve final; '
                  'inicio no garantiza estas igualdades.')
    if initial is not None:
        for i in range(len(x)):
            x[i].value = float(initial[0][i])
            x_c[i, 0].value = float(initial[1][i])

    # Dependent linear equations can make an optimizer stop at a feasible,
    # non-optimal point (e.g. identical fixed grades duplicate mass closure).
    linear_rows = []
    def constrain(expression, limit):
        if limit == 0:
            m.Equation(expression == 0)
        else:
            m.Equation(expression <= limit)
            m.Equation(expression >= -limit)

    def add_linear(coefficients, expression, limit):
        # Las bandas no admiten eliminar filas por dependencia lineal.
        if closure_mass > 0 or closure_copper > 0:
            constrain(expression, limit)
            return
        if not np.any(coefficients):
            return
        candidate = np.array(linear_rows + [coefficients])
        if np.linalg.matrix_rank(candidate) > len(linear_rows):
            linear_rows.append(coefficients)
            m.Equation(expression == 0)

    for i in row_flows:
        add_linear(matriz[i], balance_TMS[i], closure_mass)
    for k in range(n_components):
        fixed_grade = ((error.iloc[:, k+1].to_numpy() == 0)
                       | (mediciones_leyes[k] == 0) | (tms_medicion == 0))
        for i in row_flows:
            involved = matriz[i] != 0
            if np.all(fixed_grade[involved]):
                add_linear(matriz[i] * mediciones_leyes[k], balances[k][i], closure_copper)
            else:
                constrain(balances[k][i], closure_copper)

    # F25/F29 are definitional Cu-transfer equalities for the 125-flow
    # catalog. They remain exact even when ordinary nodal Cu closures use a
    # nonzero tolerance. F70 is the aggregate flow and appears exactly once.
    enforced_transfer_rules = []
    for name, coefficients in transfer_rules:
        implied_by_exact_nodes = (closure_copper == 0
                                  and _transfer_rule_is_implied(coefficients, topology))
        if implied_by_exact_nodes:
            continue
        expression = sum(float(coefficients[j]) * x[j] * x_c[j, 0]
                         for j in np.flatnonzero(coefficients))
        m.Equation(expression == 0)
        enforced_transfer_rules.append((name, coefficients))

    for _, coefficients, gap in mass_rules:
        m.Equation(sum(float(coefficients[j]) * x[j]
                       for j in np.flatnonzero(coefficients)) >= gap)

    m.solver_options = [
        "mu_strategy adaptive",
        "nlp_scaling_method gradient-based",
        "warm_start_init_point yes",
        "warm_start_bound_push 1e-9",
        "warm_start_mult_bound_push 1e-9",
        "tol 1e-10",
        "constr_viol_tol 1e-10",
        "acceptable_constr_viol_tol 1e-10",
        "acceptable_iter 100",
        f"max_iter {max_iter}",
    ]
    m.options.COLDSTART = 0
    m.options.MAX_ITER = max_iter
    # Tighten numerical convergence without widening physical closure bands.
    m.options.RTOL = 1e-10
    m.options.OTOL = 1e-10
    m.options.DIAGLEVEL = 1 if solver_verbose else 0
    def report_failure(reason):
        try:
            from reconciliation.solver_report import print_failure_report
            print_failure_report(topology, mediciones_input, error, m.path, reason,
                                 mass_names=[v.name for v in x],
                                 grade_names=[x_c[i, 0].name for i in range(len(x))],
                                 full_logs=solver_verbose, closure_mass=closure_mass, closure_copper=closure_copper)
        except Exception as diagnostic_error:
            print(f'No se pudo completar el diagnóstico: {diagnostic_error}. Archivos: {m.path}')
    def gekko_scalar(variable, fallback):
        """Read GEKKO values whether its API exposes a scalar or a 1-item list."""
        value = variable.value
        # GK_Value wraps both Python scalars (before solve) and lists (after
        # loading results); indexing its scalar payload raises TypeError.
        value = getattr(value, 'value', value)
        try:
            return float(value)
        except (TypeError, ValueError):
            try:
                return float(value[0])
            except (TypeError, IndexError, ValueError):
                return float(fallback)

    # Keep the feasible start so Dash can still show useful numbers if GEKKO
    # cannot load an iterate after an unsuccessful solve.
    fallback_mass = np.array([gekko_scalar(v, tms_medicion[i]) for i, v in enumerate(x)])
    fallback_grade = np.array([
        gekko_scalar(x_c[i, 0], mediciones_leyes[0][i]) for i in range(len(x))
    ])
    solver_error = None
    solve_started = perf_counter()
    try:
        # GEKKO debug=1 raises immediately on APMonitor @error. debug=0 lets
        # GEKKO attempt to load results.json, which may contain a last iterate.
        m.solve(disp=solver_verbose, debug=0)
    except Exception as exc:
        solver_error = str(exc)
    solve_seconds = perf_counter() - solve_started
    if solver_error and solver_verbose:
        report_failure(solver_error)

    x_c_values = np.empty((x_c.shape[0], n_components))
    x_values = np.empty(x.shape[0])
    for i in range(x.shape[0]):
        x_values[i] = gekko_scalar(x[i], fallback_mass[i])

    for k in range(n_components):
        for i in range(x_c.shape[0]):
            x_c_values[i, k] = gekko_scalar(x_c[i, k], fallback_grade[i])

    if not np.isfinite(x_values).all():
        x_values = fallback_mass.copy()
    if not np.isfinite(x_c_values).all():
        x_c_values[:, 0] = fallback_grade

    M_finos = np.zeros((x_values.shape[0], n_components))
    for k in range(n_components):
        M_finos[:, k] = np.multiply(x_values, x_c_values[:, k])

    b_fino_Cu = np.dot(matriz, M_finos[:, 0])
    b_masa = np.dot(matriz, x_values)

    transfer_results = []
    for name, coefficients in transfer_rules:
        residual = float(coefficients @ M_finos[:, 0])
        scale = max(1.0, float(np.abs(coefficients) @ np.abs(M_finos[:, 0])))
        # GEKKO/IPOPT can leave sub-microton residuals on a satisfied
        # nonlinear equality; this is a numerical validation threshold only,
        # not a copper-closure band in the optimization model.
        limit = 1e-6 + 1e-10 * scale
        transfer_results.append(dict(regla=name, residuo_t_Cu=residual,
                                     limite_t_Cu=limit, cumple=abs(residual) <= limit))
    transfer_rules_ok = all(rule['cumple'] for rule in transfer_results)

    # Solver success alone is not sufficient: verify physical closure.
    active = topology.balance_rows
    mass_scale = np.maximum(1.0, np.abs(matriz) @ x_values)
    fine_scale = np.maximum(1.0, np.abs(matriz) @ np.abs(M_finos[:, 0]))
    mass_limits = closure_mass + 1e-8 + 1e-10 * mass_scale
    copper_limits = closure_copper + 1e-8 + 1e-10 * fine_scale
    closure_ok = (np.isfinite(x_values).all() and np.isfinite(x_c_values).all()
            and not np.any(np.abs(b_masa[active]) > mass_limits[active])
            and not np.any(np.abs(b_fino_Cu[active]) > copper_limits[active])
            and transfer_rules_ok)
    app_status = getattr(m.options, 'APPSTATUS', None)
    solve_status = getattr(m.options, 'SOLVESTATUS', None)
    solver_ok = solver_error is None and app_status == 1 and solve_status == 1
    mass_rule_results = [dict(regla=name, diferencia_t=float(coefficients @ x_values),
        minimo_t=gap, cumple=bool(coefficients @ x_values >= gap - MASS_COMPARISON_TOL))
        for name, coefficients, gap in mass_rules]
    mass_rules_ok = all(rule['cumple'] for rule in mass_rule_results)
    mass_rule_issues = ' '.join(
        f"{rule['regla']}: diferencia={rule['diferencia_t']:.8g} t; mínimo={rule['minimo_t']:.8g} t."
        for rule in mass_rule_results if not rule['cumple'])
    if not closure_ok and solver_verbose and not solver_error:
        report_failure('El optimizador terminó, pero el resultado no supera la validación de cierre.')
    active_indices = np.flatnonzero(active)

    def closure_detail(label, residual, limits):
        # Show the node furthest outside its own numerical threshold, which
        # need not be the node with the largest absolute residual.
        i = active_indices[np.argmax(np.abs(residual[active]) / limits[active])]
        return (f'{label}: |residuo|={abs(residual[i]):.8g} t; '
                f'límite={limits[i]:.8g} t ({nodos_names[i]})')

    details = (closure_detail('Masa', b_masa, mass_limits) + '. '
               + closure_detail('Cobre', b_fino_Cu, copper_limits) + '.')
    failed_transfers = [rule for rule in transfer_results if not rule['cumple']]
    if failed_transfers:
        details += ' Transferencias Cu fuera de igualdad: ' + '; '.join(
            f"{r['regla']} residual={r['residuo_t_Cu']:.8g} t Cu, límite={r['limite_t_Cu']:.8g} t Cu"
            for r in failed_transfers) + '.'
    if not closure_ok:
        result_state = 'unclosed'
        result_status = (f'BALANCES FUERA DE TOLERANCIA: {details} '
                         f'{mass_rule_issues} Se muestran valores provisionales. Diagnóstico GEKKO: {m.path}')
    elif not mass_rules_ok:
        result_state = 'mass_constraints_violated'
        result_status = (f'RESTRICCIONES DE MASA INCUMPLIDAS: {mass_rule_issues} '
                         f'Los balances cierran, pero los valores son provisionales. Diagnóstico GEKKO: {m.path}')
    elif not solver_ok:
        result_state = 'closed_unconfirmed'
        issue = solver_error or (f'GEKKO no confirmó la convergencia del objetivo '
                                 f'(APPSTATUS={app_status}, SOLVESTATUS={solve_status}, '
                                 f'máximo de iteraciones={max_iter}).')
        result_status = (f'BALANCES CERRADOS: {details} La optimización no está confirmada. '
                         f'{issue} Se muestran los valores disponibles del solver o del punto inicial. '
                         f'Diagnóstico GEKKO: {m.path}')
    else:
        result_state = 'validated'
        result_status = 'Convergencia GEKKO y cierre físico validados.'

    # --- VECTORIZED ERROR CALCULATION ---
    def get_error(x_val, m_val):
        safe = np.where(m_val != 0, m_val, 1.0)
        ratio = (x_val - m_val) / safe * 100.0
        return np.where(m_val == 0, np.where(x_val > 0, 100.0, 0.0), ratio)

    b_masa_ini = np.dot(matriz, mediciones[:, 0])
    b_fino_ini_Cu = np.dot(matriz, mediciones[:, 0] * mediciones[:, 1])

    resultados = pd.DataFrame({"Flujo": nombres_flujos, "Codigo": topology.codes})
    resultados["Masa medida"] = np.multiply(mediciones[:, 0], inventarios_masa)
    resultados["Masa recon"] = np.multiply(x_values, inventarios_masa)
    resultados["Error masa"] = get_error(x_values, mediciones[:, 0])

    resultados["Ley medida Cu"] = mediciones[:, 1] * 100
    resultados["Ley recon Cu" ] = x_c_values[:, 0] * 100
    resultados["Error ley Cu"] = get_error(x_c_values[:, 0], mediciones[:, 1])

    resultados["Fino medida Cu"] = mediciones[:, 1] * mediciones[:, 0] * inventarios_masa
    resultados["Fino recon Cu" ] = x_c_values[:, 0] * x_values * inventarios_masa
    resultados["Error Fino Cu"] = get_error(x_c_values[:, 0] * x_values, mediciones[:, 0] * mediciones[:, 1])
    resultados.attrs['solver_status'] = result_status
    resultados.attrs['result_state'] = result_state
    resultados.attrs['closure_ok'] = bool(closure_ok)
    resultados.attrs['solver_converged'] = bool(solver_ok)
    resultados.attrs['mass_constraints_ok'] = mass_rules_ok
    resultados.attrs['mass_constraints'] = mass_rule_results
    resultados.attrs['transfer_constraints_ok'] = transfer_rules_ok
    resultados.attrs['transfer_constraints'] = transfer_results
    resultados.attrs['transfer_constraints_enforced'] = [name for name, _ in enforced_transfer_rules]
    resultados.attrs['timings'] = {
        'inicio_factible_s': feasibility_seconds,
        'construccion_s': solve_started - started - feasibility_seconds,
        'solver_s': solve_seconds,
        'total_s': perf_counter() - started,
    }

    masa_df = pd.DataFrame(nodos_names, columns=["Nodo"])
    masa_df["Desbalance masa inicial"] = b_masa_ini
    masa_df["Desbalance masa"] = b_masa
    masa_df["Desbalance fino inicial Cu"] = b_fino_ini_Cu
    masa_df["Desbalance fino Cu"] = b_fino_Cu
    masa_df["Reconciliar"] = topology.balance_rows
    masa_ini = pd.DataFrame(nodos_names)
    return resultados, masa_df, masa_ini, matriz
