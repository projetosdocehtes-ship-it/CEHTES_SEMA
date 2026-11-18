class Protocolo:
    # Inicializar o objeto
    def __init__(self, protocolo_id=0, pedido_id=0, pedido_item_id=0) -> None:
        self.protocolo_id = protocolo_id
        self.pedido_id = pedido_id
        self.pedido_item_id = pedido_item_id

    # Retornar o numero do protocolo
    def numero_protocolo(self):
        return self.protocolo_id

    # Retornar o numero do protocolo
    def valores_totais(self):
        return list[1, 2, 3, 4, 5, 6, 7]


# Criar os valores
protocolo_id, pedido_id, pedido_item_id = 0, 0, 0

# Instanciar o objeto
protocolo = Protocolo(protocolo_id)

# print(protocolo.valores_totais())
