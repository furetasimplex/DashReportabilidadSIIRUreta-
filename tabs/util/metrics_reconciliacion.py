def preparar_metricas(df):
    df = df.copy()

    df["delta_abs"] = df["valor_reconciliado"] - df["valor_medido"]
    df["delta_pct"] = (df["delta_abs"] / df["valor_medido"]) * 100

    df["cumple_tol"] = (
        df["delta_pct"].abs() <= df["tolerancia_pct"]
    )

    df["severidad"] = (
        df["delta_pct"].abs() / df["tolerancia_pct"]
    )

    return df