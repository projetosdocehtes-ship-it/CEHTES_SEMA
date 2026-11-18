def _safe_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def simular_diagrama(layout_json: dict) -> dict:
    nodes = layout_json.get("nodes", []) or []
    edges = layout_json.get("edges", []) or []

    alertas = []
    total_potencia_kw = 0.0
    total_energia_kwh = 0.0

    nodes_by_id = {node.get("id"): node for node in nodes}

    tipos = []
    for node in nodes:
        componente = (node.get("data") or {}).get("componente") or {}
        tipos.append(componente.get("tipo_codigo"))
        total_potencia_kw += _safe_float(componente.get("potencia_kw"))
        total_energia_kwh += _safe_float(componente.get("energia_kwh"))

        tipo_codigo = componente.get("tipo_codigo")
        label = (node.get("data") or {}).get("label") or node.get("id")

        if tipo_codigo == "bateria" and not componente.get("energia_kwh"):
            alertas.append(f"A bateria '{label}' está sem energia_kwh cadastrada.")

        if tipo_codigo in {"inversor", "pcs", "transformador"} and not componente.get("potencia_kw"):
            alertas.append(f"O componente '{label}' está sem potencia_kw cadastrada.")

    if "poc" not in tipos:
        alertas.append("O diagrama não possui Ponto de Conexão (POC).")

    if "transformador" not in tipos:
        alertas.append("O diagrama não possui transformador.")

    bateria_ids = set()
    inversor_ids = set()
    pcs_ids = set()
    barramento_ids = set()

    for node in nodes:
        componente = (node.get("data") or {}).get("componente") or {}
        tipo = componente.get("tipo_codigo")
        node_id = node.get("id")
        if tipo == "bateria":
            bateria_ids.add(node_id)
        elif tipo == "inversor":
            inversor_ids.add(node_id)
        elif tipo == "pcs":
            pcs_ids.add(node_id)
        elif tipo == "barramento":
            barramento_ids.add(node_id)

    bateria_ligada_ao_pcs = False
    pcs_ligado_ao_barramento = False

    for edge in edges:
        source = edge.get("source")
        target = edge.get("target")

        if not source or not target:
            alertas.append("Existe uma conexão sem origem ou destino.")
            continue

        source_tipo = (((nodes_by_id.get(source) or {}).get("data") or {}).get("componente") or {}).get("tipo_codigo")
        target_tipo = (((nodes_by_id.get(target) or {}).get("data") or {}).get("componente") or {}).get("tipo_codigo")

        if source_tipo == "bateria" and target_tipo == "inversor":
            alertas.append("Bateria ligada diretamente em inversor FV. Use PCS.")
        if source_tipo == "inversor" and target_tipo == "bateria":
            alertas.append("Inversor FV ligado diretamente em bateria. Use PCS.")

        if (source in bateria_ids and target in pcs_ids) or (source in pcs_ids and target in bateria_ids):
            bateria_ligada_ao_pcs = True

        if (source in pcs_ids and target in barramento_ids) or (source in barramento_ids and target in pcs_ids):
            pcs_ligado_ao_barramento = True

    if bateria_ids and not pcs_ids:
        alertas.append("Há bateria no projeto, mas não existe PCS.")

    if bateria_ids and pcs_ids and not bateria_ligada_ao_pcs:
        alertas.append("A bateria não está conectada ao PCS.")

    if pcs_ids and barramento_ids and not pcs_ligado_ao_barramento:
        alertas.append("O PCS não está conectado ao barramento.")

    return {
        "status": "ok" if not alertas else "atencao",
        "resumo": {
            "quantidade_nos": len(nodes),
            "quantidade_ligacoes": len(edges),
            "potencia_total_kw": round(total_potencia_kw, 2),
            "energia_total_kwh": round(total_energia_kwh, 2),
        },
        "alertas": alertas,
    }
