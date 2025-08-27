import tkinter as tk
from tkinter import scrolledtext
from tkinter import ttk
from googlesearch import search
import requests
from bs4 import BeautifulSoup
from bs4.element import Tag
import json
import re
import threading
import webbrowser
from tkinter import filedialog, messagebox
from openpyxl import Workbook

# -------------------------------------------
# Listas e cache
# -------------------------------------------

UFS = [
    ("AC", "Acre"), ("AL", "Alagoas"), ("AP", "Amapá"), ("AM", "Amazonas"),
    ("BA", "Bahia"), ("CE", "Ceará"), ("DF", "Distrito Federal"), ("ES", "Espírito Santo"),
    ("GO", "Goiás"), ("MA", "Maranhão"), ("MT", "Mato Grosso"), ("MS", "Mato Grosso do Sul"),
    ("MG", "Minas Gerais"), ("PA", "Pará"), ("PB", "Paraíba"), ("PR", "Paraná"),
    ("PE", "Pernambuco"), ("PI", "Piauí"), ("RJ", "Rio de Janeiro"), ("RN", "Rio Grande do Norte"),
    ("RS", "Rio Grande do Sul"), ("RO", "Rondônia"), ("RR", "Roraima"), ("SC", "Santa Catarina"),
    ("SP", "São Paulo"), ("SE", "Sergipe"), ("TO", "Tocantins")
]
MUNICIPIOS_CACHE = {}
SEARCH_RESULTS = []

# -------------------------------------------
# Utilitários
# -------------------------------------------

def _headers():
    return {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}

def _limpa_tel(t: str) -> str:
    return re.sub(r'\D', '', t or '')

def _uniq(seq):
    return list(dict.fromkeys([s for s in seq if s]))

def _iter_hrefs(soup: BeautifulSoup):
    """
    Itera com segurança por todos os hrefs:
    lida com href sendo str OU lista (AttributeValueList).
    Evita erros de tipagem do Pylance/BS4.
    """
    for node in soup.find_all('a'):
        if not isinstance(node, Tag):
            continue
        href_val = node.get('href', None)
        if isinstance(href_val, list):
            for hv in href_val:
                if isinstance(hv, str):
                    yield hv
        elif isinstance(href_val, str):
            yield href_val

def _extrai_jsonld(soup: BeautifulSoup):
    """Extrai telefone/e-mail/endereço/redes de possíveis blocos JSON-LD."""
    tels, emails, enderecos, redes = [], [], [], []
    for node in soup.find_all('script', type='application/ld+json'):
        if not isinstance(node, Tag):
            continue
        try:
            raw = node.string if hasattr(node, "string") and node.string is not None else node.get_text()  # type: ignore[attr-defined]
            data = json.loads(raw or '')
        except Exception:
            continue
        blocos = data if isinstance(data, list) else [data]
        for b in blocos:
            if not isinstance(b, dict):
                continue
            tel = b.get('telephone')
            if isinstance(tel, list):
                tels.extend(tel)
            elif tel:
                tels.append(tel)

            email = b.get('email')
            if isinstance(email, list):
                emails.extend(email)
            elif email:
                emails.append(email)

            addr = b.get('address')
            if isinstance(addr, dict):
                linha = " ".join(_uniq([
                    addr.get('streetAddress', ''),
                    addr.get('addressLocality', ''),
                    addr.get('addressRegion', ''),
                    addr.get('postalCode', ''),
                    addr.get('addressCountry', ''),
                ])).strip()
                if linha:
                    enderecos.append(linha)

            same_as = b.get('sameAs')
            if isinstance(same_as, list):
                redes.extend(same_as)
            elif isinstance(same_as, str):
                redes.append(same_as)

    return _uniq(tels), _uniq(emails), _uniq(enderecos), _uniq(redes)

# -------------------------------------------
# Busca (Google)
# -------------------------------------------

def buscar_sites(consulta, num_sites=10):
    """
    Compatível com 'googlesearch' e 'googlesearch-python' sem depender de kwargs específicos.
    Busca e limita localmente a quantidade retornada.
    """
    try:
        results = list(search(consulta))
    except TypeError:
        # Fallback sem kwargs (alguns ambientes variam a assinatura)
        try:
            results = list(search(consulta))
        except Exception as e2:
            print(f"Erro ao buscar sites para '{consulta}': {e2}")
            return []
    except Exception as e:
        print(f"Erro ao buscar sites para '{consulta}': {e}")
        return []
    # Limita a quantidade localmente
    return results[:num_sites]

# -------------------------------------------
# Extração de dados por página
# -------------------------------------------

def extrair_emails_telefones_enderecos(url, buscar_email, buscar_tel, buscar_endereco):
    """Retorna SEMPRE 3 listas (emails, telefones, enderecos)."""
    try:
        resp = requests.get(url, headers=_headers(), timeout=10)
        if resp.status_code != 200:
            return [], [], []
        soup = BeautifulSoup(resp.text, 'html.parser')
        texto = soup.get_text(separator=' ', strip=True)

        tel_ld, email_ld, end_ld, _ = _extrai_jsonld(soup)

        emails, telefones, enderecos = [], [], []

        if buscar_email:
            emails = re.findall(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", texto)
            for href in _iter_hrefs(soup):
                if isinstance(href, str) and href.lower().startswith('mailto:'):
                    emails.append(href.replace('mailto:', '').split('?')[0])

        if buscar_tel:
            for h in _iter_hrefs(soup):
                if not isinstance(h, str):
                    continue
                low = h.lower()
                if low.startswith('tel:'):
                    telefones.append(h.replace('tel:', ''))
                if 'wa.me/' in low or 'whatsapp.com/send' in low:
                    telefones.append('WhatsApp')
            telefones += re.findall(r"\(?\d{2}\)?\s?\d{4,5}[-\s]?\d{4}", texto)
            telefones = _uniq([t for t in telefones if len(_limpa_tel(t)) >= 10 or t == 'WhatsApp'])

        if buscar_endereco:
            padrao_end = r"\b(?:Rua|Avenida|Av\.|Travessa|Praça|Rodovia|Estrada|Alameda|Largo|BR-|SP-|RJ-)\s+[^\n,]{3,120}"
            enderecos = re.findall(padrao_end, texto)

        if buscar_tel:
            telefones = _uniq(telefones + tel_ld)
        if buscar_email:
            emails = _uniq(emails + email_ld)
        if buscar_endereco:
            enderecos = _uniq(enderecos + end_ld)

        return emails, telefones, enderecos
    except Exception as e:
        print(f"Erro ao acessar {url}: {e}")
        return [], [], []

def extrair_infos(url, buscar_email, buscar_tel, buscar_endereco, buscar_site, buscar_social):
    """
    Retorna 5 listas: emails, telefones, enderecos, outros_sites, redes_sociais.
    """
    try:
        resp = requests.get(url, headers=_headers(), timeout=10)
        if resp.status_code != 200:
            return [], [], [], [], []
        soup = BeautifulSoup(resp.text, 'html.parser')
        texto = soup.get_text(separator=' ', strip=True)

        tel_ld, email_ld, end_ld, redes_ld = _extrai_jsonld(soup)

        emails, telefones, enderecos, sites, redes_sociais = [], [], [], [], []

        if buscar_email:
            emails = re.findall(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", texto)
            for href in _iter_hrefs(soup):
                if isinstance(href, str) and href.lower().startswith('mailto:'):
                    emails.append(href.replace('mailto:', '').split('?')[0])

        if buscar_tel:
            for h in _iter_hrefs(soup):
                if not isinstance(h, str):
                    continue
                low = h.lower()
                if low.startswith('tel:'):
                    telefones.append(h.replace('tel:', ''))
                if 'wa.me/' in low or 'whatsapp.com/send' in low:
                    telefones.append('WhatsApp')
            telefones += re.findall(r"\(?\d{2}\)?\s?\d{4,5}[-\s]?\d{4}", texto)
            telefones = _uniq([t for t in telefones if len(_limpa_tel(t)) >= 10 or t == 'WhatsApp'])

        if buscar_endereco:
            padrao_end = r"\b(?:Rua|Avenida|Av\.|Travessa|Praça|Rodovia|Estrada|Alameda|Largo|BR-|SP-|RJ-)\s+[^\n,]{3,120}"
            enderecos = re.findall(padrao_end, texto)

        if buscar_site or buscar_social:
            for href in _iter_hrefs(soup):
                if not isinstance(href, str):
                    continue
                low = href.lower()
                if not low.startswith('http'):
                    continue
                if buscar_social and any(s in low for s in ['facebook.com', 'instagram.com', 'twitter.com', 'x.com', 'linkedin.com', 'wa.me', 'whatsapp.com']):
                    redes_sociais.append(href)
                elif buscar_site:
                    sites.append(href)

        if buscar_tel:
            telefones = _uniq(telefones + tel_ld)
        if buscar_email:
            emails = _uniq(emails + email_ld)
        if buscar_endereco:
            enderecos = _uniq(enderecos + end_ld)
        if buscar_social:
            redes_sociais = _uniq(redes_sociais + redes_ld)

        return emails, telefones, enderecos, _uniq(sites), redes_sociais
    except Exception as e:
        print(f"Erro ao acessar {url}: {e}")
        return [], [], [], [], []

# -------------------------------------------
# UI helpers (links clicáveis, render, etc.)
# -------------------------------------------

def insert_link(widget: tk.Text, url: str, display_text: str | None = None):
    """Insere um link clicável com cursor de mão."""
    if not display_text:
        display_text = url
    start = widget.index(tk.END)
    widget.insert(tk.END, display_text)
    end = widget.index(tk.END)
    tag = f"link_{start.replace('.', '_')}"
    widget.tag_add(tag, start, end)
    widget.tag_config(tag, foreground="blue", underline=True)

    def _open(_e=None, link=url):
        try:
            webbrowser.open_new(link)
        except Exception:
            pass
    def _enter(_e=None):
        widget.config(cursor="hand2")
    def _leave(_e=None):
        widget.config(cursor="arrow")

    widget.tag_bind(tag, "<Button-1>", _open)
    widget.tag_bind(tag, "<Enter>", _enter)
    widget.tag_bind(tag, "<Leave>", _leave)

def render_results(results):
    """Mostra resultados com links clicáveis (urls, e-mails, telefones)."""
    try:
        resultado_text.delete(1.0, tk.END)
        resultado_text.insert(tk.END, "=== Resultados ===\n")

        if not results:
            resultado_text.insert(tk.END, "\nNenhum site foi encontrado para a consulta.\n")
            return

        for item in results:
            site = item.get("site", "")
            emails = item.get("emails", [])
            telefones = item.get("telefones", [])
            enderecos = item.get("enderecos", [])
            outros_sites = item.get("outros_sites", [])
            redes_sociais = item.get("redes_sociais", [])

            resultado_text.insert(tk.END, "\n🔗 Site: ")
            if site:
                insert_link(resultado_text, site, site)
            resultado_text.insert(tk.END, "\n")

            # e-mails -> mailto:
            if emails:
                resultado_text.insert(tk.END, "📧 E-mails encontrados:\n")
                for email in emails:
                    resultado_text.insert(tk.END, "   - ")
                    insert_link(resultado_text, f"mailto:{email}", email)
                    resultado_text.insert(tk.END, "\n")
            else:
                resultado_text.insert(tk.END, "Nenhum e-mail encontrado.\n")

            # telefones -> tel:
            if telefones:
                resultado_text.insert(tk.END, "📞 Telefones encontrados:\n")
                for tel in telefones:
                    resultado_text.insert(tk.END, "   - ")
                    if isinstance(tel, str) and tel.lower() == "whatsapp":
                        resultado_text.insert(tk.END, "WhatsApp\n")
                    else:
                        tel_digits = re.sub(r"\D", "", tel)
                        if tel_digits:
                            insert_link(resultado_text, f"tel:{tel_digits}", tel)
                            resultado_text.insert(tk.END, "\n")
                        else:
                            resultado_text.insert(tk.END, f"{tel}\n")
            else:
                resultado_text.insert(tk.END, "Nenhum telefone encontrado.\n")

            # endereços (texto simples)
            if enderecos:
                resultado_text.insert(tk.END, "🏠 Endereços encontrados:\n")
                for end in enderecos:
                    resultado_text.insert(tk.END, f"   - {end}\n")
            else:
                resultado_text.insert(tk.END, "Nenhum endereço encontrado.\n")

            # outros sites
            if outros_sites:
                resultado_text.insert(tk.END, "🌐 Outros sites encontrados:\n")
                for s in outros_sites:
                    resultado_text.insert(tk.END, "   - ")
                    insert_link(resultado_text, s, s)
                    resultado_text.insert(tk.END, "\n")
            else:
                resultado_text.insert(tk.END, "Nenhum site encontrado.\n")

            # redes sociais
            if redes_sociais:
                resultado_text.insert(tk.END, "🔗 Redes sociais encontradas:\n")
                for r in redes_sociais:
                    resultado_text.insert(tk.END, "   - ")
                    insert_link(resultado_text, r, r)
                    resultado_text.insert(tk.END, "\n")
            else:
                resultado_text.insert(tk.END, "Nenhuma rede social encontrada.\n")

    except Exception as e:
        print(f"Erro ao renderizar resultados: {e}")

# -------------------------------------------
# UF / Município
# -------------------------------------------

def carregar_estados():
    ufs_legiveis = [f"{sigla} - {nome}" for sigla, nome in UFS]
    estado_combo["values"] = ufs_legiveis
    estado_combo.set("")
    cidade_combo.set("")
    cidade_combo["values"] = []

def on_estado_selecionado(event=None):
    valor = estado_combo.get().strip()
    if not valor:
        cidade_combo["values"] = []
        cidade_combo.set("")
        return
    sigla = valor.split(" - ")[0]
    if sigla in MUNICIPIOS_CACHE:
        cidade_combo["values"] = MUNICIPIOS_CACHE[sigla]
        cidade_combo.set("")
        return
    try:
        url = f"https://servicodados.ibge.gov.br/api/v1/localidades/estados/{sigla}/municipios"
        resp = requests.get(url, headers=_headers(), timeout=10)
        if resp.status_code == 200:
            dados = resp.json()
            cidades = sorted([item.get("nome", "") for item in dados if item.get("nome")])
            MUNICIPIOS_CACHE[sigla] = cidades
            cidade_combo["values"] = cidades
            cidade_combo.set("")
        else:
            cidade_combo["values"] = []
            cidade_combo.set("")
        root.update_idletasks()
    except Exception as e:
        print(f"Erro ao buscar municípios do IBGE ({sigla}): {e}")
        cidade_combo["values"] = []
        cidade_combo.set("")

def get_localidade_text():
    uf = estado_combo.get().strip()
    cidade = cidade_combo.get().strip()
    sigla = uf.split(" - ")[0] if (" - " in uf) else uf
    if cidade and sigla:
        return f"{cidade} - {sigla}"
    if sigla:
        return sigla
    return ""

# -------------------------------------------
# Thread de busca
# -------------------------------------------

def buscar_thread():
    busca = entry_busca.get().strip()
    localidade = entry_localidade.get().strip()
    cidade = get_localidade_text()
    buscar_email = var_email.get()
    buscar_tel = var_tel.get()
    buscar_endereco = var_endereco.get()
    buscar_site = var_site.get()
    buscar_social = var_social.get()

    if not (buscar_email or buscar_tel or buscar_endereco or buscar_site or buscar_social):
        root.after(0, lambda: (resultado_text.delete(1.0, tk.END),
                               resultado_text.insert(tk.END, "Selecione pelo menos uma opção para buscar.\n")))
    elif not busca:
        root.after(0, lambda: (resultado_text.delete(1.0, tk.END),
                               resultado_text.insert(tk.END, "Digite o que você quer procurar no primeiro campo.\n")))
    else:
        consulta = " ".join([p for p in [busca, localidade, cidade] if p])
        sites = buscar_sites(consulta, num_sites=10)

        results = []
        for site in sites:
            emails, telefones, enderecos, outros_sites, redes_sociais = extrair_infos(
                site, buscar_email, buscar_tel, buscar_endereco, buscar_site, buscar_social
            )
            results.append({
                "site": site,
                "emails": emails if buscar_email else [],
                "telefones": telefones if buscar_tel else [],
                "enderecos": enderecos if buscar_endereco else [],
                "outros_sites": outros_sites if buscar_site else [],
                "redes_sociais": redes_sociais if buscar_social else [],
            })

        def _apply_results():
            global SEARCH_RESULTS
            SEARCH_RESULTS = results
            render_results(results)

        root.after(0, _apply_results)

def buscar():
    threading.Thread(target=buscar_thread, daemon=True).start()

def limpar_total():
    try:
        entry_busca.delete(0, tk.END)
        entry_localidade.delete(0, tk.END)
        estado_combo.set("")
        cidade_combo.set("")
        cidade_combo["values"] = []
        var_email.set(True)
        var_tel.set(True)
        var_endereco.set(False)
        var_site.set(False)
        var_social.set(False)
        resultado_text.delete(1.0, tk.END)
        global SEARCH_RESULTS
        SEARCH_RESULTS = []
    except Exception as e:
        print(f"Erro ao limpar: {e}")

def gerar_planilha():
    try:
        if not SEARCH_RESULTS:
            messagebox.showinfo("Gerar planilha", "Nenhum dado para exportar. Faça uma busca primeiro.")
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel", "*.xlsx")],
            title="Salvar planilha"
        )
        if not path:
            return

        wb = Workbook()
        # remove sheet padrão e cria outra nomeada (evita ws=None)
        default_ws = wb.active
        if default_ws is not None:
            wb.remove(default_ws)
        ws = wb.create_sheet(title="Resultados", index=0)

        ws.append(["Site", "E-mails", "Telefones", "Endereços", "Outros Sites", "Redes Sociais"])
        for item in SEARCH_RESULTS:
            ws.append([
                item.get("site", ""),
                ", ".join(item.get("emails", [])),
                ", ".join(item.get("telefones", [])),
                " | ".join(item.get("enderecos", [])),
                ", ".join(item.get("outros_sites", [])),
                ", ".join(item.get("redes_sociais", [])),
            ])
        wb.save(path)
        messagebox.showinfo("Gerar planilha", f"Planilha salva em:\n{path}")
    except Exception as e:
        messagebox.showerror("Gerar planilha", f"Erro ao salvar planilha:\n{e}")

# -------------------------------------------
# Interface gráfica
# -------------------------------------------

root = tk.Tk()
root.title("Raspador de E-mail, Telefone e Endereço")
root.geometry("1100x750")
root.minsize(900, 600)

tk.Label(root, text="O que você quer procurar?").pack()
entry_busca = tk.Entry(root, width=50)
entry_busca.pack()

tk.Label(root, text="Bairro/Localidade (opcional)").pack()
entry_localidade = tk.Entry(root, width=50)
entry_localidade.pack()

tk.Label(root, text="Estado (UF)").pack()
estado_combo = ttk.Combobox(root, width=50, state="readonly")
estado_combo.pack()
estado_combo.bind("<<ComboboxSelected>>", on_estado_selecionado)

tk.Label(root, text="Cidade (município)").pack()
cidade_combo = ttk.Combobox(root, width=50)
cidade_combo.pack()

frame_opcoes = tk.Frame(root)
frame_opcoes.pack(pady=5)

var_email = tk.BooleanVar(value=True)
var_tel = tk.BooleanVar(value=True)
var_endereco = tk.BooleanVar(value=False)
var_site = tk.BooleanVar(value=False)
var_social = tk.BooleanVar(value=False)

tk.Checkbutton(frame_opcoes, text="E-mail", variable=var_email).pack(side=tk.LEFT, padx=5)
tk.Checkbutton(frame_opcoes, text="Telefone", variable=var_tel).pack(side=tk.LEFT, padx=5)
tk.Checkbutton(frame_opcoes, text="Endereço", variable=var_endereco).pack(side=tk.LEFT, padx=5)
tk.Checkbutton(frame_opcoes, text="Site", variable=var_site).pack(side=tk.LEFT, padx=5)
tk.Checkbutton(frame_opcoes, text="Rede Social", variable=var_social).pack(side=tk.LEFT, padx=5)

btn_frame = tk.Frame(root)
btn_frame.pack(pady=10)
tk.Button(btn_frame, text="Buscar", command=buscar).pack(side=tk.LEFT, padx=5)
tk.Button(btn_frame, text="Limpar", command=limpar_total).pack(side=tk.LEFT, padx=5)
tk.Button(btn_frame, text="Gerar Planilha", command=gerar_planilha).pack(side=tk.LEFT, padx=5)

# Área de resultados maior e expansível
resultado_frame = tk.Frame(root)
resultado_frame.pack(fill="both", expand=True, padx=10, pady=10)
resultado_text = scrolledtext.ScrolledText(resultado_frame, wrap="word")
resultado_text.pack(fill="both", expand=True)

# Somente leitura sem state='disabled' (para manter links clicáveis)
def _make_text_readonly(widget: tk.Text):
    for seq in ("<Key>", "<Control-v>", "<Control-V>", "<<Paste>>",
                "<Button-2>", "<BackSpace>", "<Delete>",
                "<Control-x>", "<Control-X>"):
        widget.bind(seq, lambda e: "break")
    widget.config(cursor="arrow")

_make_text_readonly(resultado_text)

carregar_estados()
root.mainloop()