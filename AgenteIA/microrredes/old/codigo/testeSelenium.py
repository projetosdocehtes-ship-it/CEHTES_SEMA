from seleniumbase import SB

with SB(uc=True) as sb:
    # Open protected page with reconnect handling
    sb.uc_open_with_reconnect("https://cepea.esalq.usp.br/br/consultas-ao-banco-de-dados-do-site.aspx?tabela_id=2&data_inicial=13/03/2026&periodicidade=1&data_final=10/04/2026%27", 5)
    
    # Let Cloudflare challenge complete
    sb.sleep(3)
    
    # Handle Turnstile if it appears
    sb.uc_gui_click_captcha()
    
    # Extract content
    html = sb.get_page_source()
    print(html)