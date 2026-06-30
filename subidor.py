import tkinter as tk
from tkinter import filedialog, messagebox
import os
import threading
import shutil
import tempfile
import glob
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
import time

def leer_descripcion(carpeta):
    ruta = os.path.join(carpeta, "descripcion.txt")
    datos = {}
    CLAVES_CONOCIDAS = {"TITULO", "PRECIO", "CATEGORIA", "TAGS",
                        "DESCRIPCION", "URL_GUMROAD", "URL_PAYHIP",
                        "URL_KOFI", "URL_ITCH"}
    with open(ruta, encoding="utf-8") as f:
        contenido = f.read()
    lineas = contenido.splitlines()
    en_descripcion = False
    for linea in lineas:
        if "=" in linea:
            clave, _, valor = linea.partition("=")
            clave = clave.strip()
            if clave in CLAVES_CONOCIDAS:
                en_descripcion = False
                if clave == "DESCRIPCION":
                    datos[clave] = valor.strip()
                    en_descripcion = True
                else:
                    datos[clave] = valor.strip()
                continue
        if en_descripcion:
            datos["DESCRIPCION"] += "\n" + linea
    return datos

def guardar_url(carpeta, clave, url):
    if not url or url.strip() == "":
        return
    ruta = os.path.join(carpeta, "descripcion.txt")
    with open(ruta, encoding="utf-8") as f:
        contenido = f.read()
    nuevas_lineas = []
    encontrado = False
    for linea in contenido.splitlines():
        if linea.startswith(f"{clave}="):
            nuevas_lineas.append(f"{clave}={url}")
            encontrado = True
        else:
            nuevas_lineas.append(linea)
    if not encontrado:
        nuevas_lineas.append(f"{clave}={url}")
    with open(ruta, "w", encoding="utf-8") as f:
        f.write("\n".join(nuevas_lineas))

def buscar_archivo(carpeta, extensiones):
    for archivo in os.listdir(carpeta):
        if any(archivo.lower().endswith(ext) for ext in extensiones):
            return os.path.abspath(os.path.join(carpeta, archivo))
    return None

def obtener_perfil_firefox():
    perfiles_dir = os.path.expanduser(r"~\AppData\Roaming\Mozilla\Firefox\Profiles")
    perfiles = glob.glob(os.path.join(perfiles_dir, "*.default-release"))
    if not perfiles:
        perfiles = glob.glob(os.path.join(perfiles_dir, "*"))
    return perfiles[0] if perfiles else ""

def crear_driver():
    perfil_original = obtener_perfil_firefox()
    perfil_temp = tempfile.mkdtemp(prefix="firefox_selenium_")
    if perfil_original:
        shutil.copytree(perfil_original, perfil_temp, dirs_exist_ok=True)
    for lock in ["parent.lock", "lock"]:
        ruta_lock = os.path.join(perfil_temp, lock)
        if os.path.exists(ruta_lock):
            try:
                os.remove(ruta_lock)
            except:
                pass
    opciones = webdriver.FirefoxOptions()
    opciones.add_argument("-profile")
    opciones.add_argument(perfil_temp)
    driver = webdriver.Firefox(options=opciones)
    return driver, perfil_temp

# ─────────────────────────────────────────────
#  PAYHIP
# ─────────────────────────────────────────────
def subir_payhip(driver, carpeta, datos, log):
    log("Payhip: Abriendo pagina...")
    driver.get("https://payhip.com/product/add/digital")
    wait = WebDriverWait(driver, 30)
    time.sleep(4)

    pdf = buscar_archivo(carpeta, [".pdf"])
    if not pdf:
        log("Payhip ERROR: No se encontro PDF.")
        return
    log("Payhip: Subiendo PDF...")
    inputs = wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "input[type='file']")))
    inputs[0].send_keys(pdf)
    time.sleep(6)

    log("Payhip: Escribiendo titulo...")
    titulo = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "input[placeholder='Your product title...']")))
    titulo.clear()
    titulo.send_keys(datos.get("TITULO", ""))

    log("Payhip: Escribiendo precio...")
    precio = driver.find_element(By.CSS_SELECTOR, "input[type='number']")
    precio.clear()
    precio.send_keys(datos.get("PRECIO", "10"))

    portada = buscar_archivo(carpeta, [".jpg", ".jpeg", ".png"])
    if portada:
        log("Payhip: Subiendo portada...")
        inputs2 = driver.find_elements(By.CSS_SELECTOR, "input[type='file']")
        if len(inputs2) > 1:
            inputs2[1].send_keys(portada)
        time.sleep(4)

    log("Payhip: Escribiendo descripcion...")
    desc_area = driver.find_element(By.CSS_SELECTOR, "div[contenteditable='true']")
    desc_area.click()
    desc_area.send_keys(datos.get("DESCRIPCION", ""))

    log("Payhip: Guardando...")
    btn = driver.find_element(By.XPATH, "//button[contains(text(),'Add Product')]")
    btn.click()
    time.sleep(6)

    # Capturar URL
    url = driver.current_url
    log(f"Payhip URL: {url}")
    guardar_url(carpeta, "URL_PAYHIP", url)
    log("Payhip: Listo.")

# ─────────────────────────────────────────────
#  KO-FI
# ─────────────────────────────────────────────
def subir_kofi(driver, carpeta, datos, log):
    desc_texto = datos.get("DESCRIPCION", "").strip()
    if not desc_texto:
        log("Ko-fi ERROR: La descripcion esta vacia en descripcion.txt. Saltando Ko-fi.")
        return

    log("Ko-fi: Abriendo pagina...")
    driver.get("https://ko-fi.com/shop/settings?productType=0")
    wait = WebDriverWait(driver, 30)
    time.sleep(4)

    # Cerrar modal de terminos si aparece
    try:
        btn_ok = WebDriverWait(driver, 6).until(
            EC.element_to_be_clickable((By.XPATH, "//button[text()='OK']")))
        driver.execute_script("arguments[0].click();", btn_ok)
        log("Ko-fi: Modal de terminos cerrado.")
        time.sleep(2)
    except:
        log("Ko-fi: No habia modal de terminos.")

    # Clic en Add product
    log("Ko-fi: Clic en Add product...")
    btn_add = wait.until(EC.element_to_be_clickable(
        (By.XPATH, "//button[contains(text(),'Add product')]")))
    driver.execute_script("arguments[0].click();", btn_add)
    time.sleep(3)

    # Titulo
    log("Ko-fi: Escribiendo titulo...")
    titulo_input = wait.until(EC.visibility_of_element_located((By.ID, "Name")))
    titulo_input.clear()
    titulo_input.send_keys(datos.get("TITULO", ""))
    log("Ko-fi: Titulo escrito.")

    # Detectar flujo modal o pagina unica
    try:
        btn_next = WebDriverWait(driver, 4).until(
            EC.visibility_of_element_located((By.ID, "shopModalNextStep")))
        log("Ko-fi: Flujo modal - dando Next...")
        driver.execute_script("arguments[0].click();", btn_next)
        time.sleep(4)
    except:
        log("Ko-fi: Flujo pagina unica.")
        time.sleep(1)

    # Descripcion
    log("Ko-fi: Escribiendo descripcion...")
    desc_input = None
    for selector in [
        (By.ID, "Description"),
        (By.CSS_SELECTOR, "textarea[placeholder*='details buyers']"),
        (By.CSS_SELECTOR, "textarea[placeholder*='Share all']"),
        (By.CSS_SELECTOR, "textarea[placeholder*='Share your listing']"),
        (By.CSS_SELECTOR, "textarea[name='Description']"),
    ]:
        try:
            desc_input = WebDriverWait(driver, 5).until(
                EC.visibility_of_element_located(selector))
            log(f"Ko-fi: Descripcion encontrada.")
            break
        except:
            continue

    if desc_input:
        desc_input.click()
        desc_input.clear()
        desc_input.send_keys(desc_texto)
        log("Ko-fi: Descripcion escrita.")
    else:
        log("Ko-fi ERROR: No se encontro campo de descripcion.")
        return

    # Product Summary
    try:
        summary = driver.find_element(By.CSS_SELECTOR,
            "input[placeholder*='wallpaper'], input[placeholder*='summary'], input[placeholder*='Summary']")
        summary.clear()
        summary.send_keys("Digital manual")
        log("Ko-fi: Product summary escrito.")
    except:
        log("Ko-fi: Campo product summary no encontrado, continuando...")

    # Portada
    portada = buscar_archivo(carpeta, [".jpg", ".jpeg", ".png"])
    if portada:
        log("Ko-fi: Subiendo portada...")
        try:
            inputs_dz = driver.find_elements(By.CSS_SELECTOR, "input.dz-hidden-input")
            log(f"Ko-fi: {len(inputs_dz)} inputs Dropzone para portada.")
            if inputs_dz:
                inputs_dz[0].send_keys(portada)
                log("Ko-fi: Portada enviada.")
                time.sleep(4)
        except Exception as e:
            log(f"Ko-fi AVISO portada: {e}")

    # PDF Asset
    pdf = buscar_archivo(carpeta, [".pdf"])
    if pdf:
        log("Ko-fi: Subiendo PDF en Assets...")
        try:
            input_asset = driver.execute_script("""
                var todos = document.querySelectorAll('*');
                for (var i = 0; i < todos.length; i++) {
                    var el = todos[i];
                    var txt = (el.innerText || el.textContent || '');
                    if ((txt.includes('Assets') || txt.includes('Upload a file'))
                        && el.children.length < 10) {
                        var inp = el.querySelector('input[type=file]');
                        if (inp) return inp;
                    }
                }
                return null;
            """)
            if input_asset:
                log("Ko-fi: Input Assets encontrado.")
                input_asset.send_keys(pdf)
            else:
                inputs_dz = driver.find_elements(By.CSS_SELECTOR, "input.dz-hidden-input")
                if len(inputs_dz) > 1:
                    inputs_dz[1].send_keys(pdf)
                    log("Ko-fi: PDF enviado al segundo Dropzone.")
                elif inputs_dz:
                    inputs_dz[0].send_keys(pdf)
                    log("Ko-fi: PDF enviado al unico Dropzone.")
                else:
                    log("Ko-fi ERROR: No se encontro input para PDF.")

            log("Ko-fi: Esperando carga del PDF...")
            cargado = False
            for _ in range(30):
                time.sleep(1)
                try:
                    if driver.find_elements(By.CSS_SELECTOR, ".dz-success, .dz-complete"):
                        log("Ko-fi: PDF cargado.")
                        cargado = True
                        break
                    nombres = [n.text.strip() for n in driver.find_elements(
                        By.CSS_SELECTOR, ".dz-filename span") if n.text.strip()]
                    if nombres:
                        log(f"Ko-fi: Archivo: {nombres[-1]}")
                        cargado = True
                        break
                except:
                    pass
            if not cargado:
                log("Ko-fi: AVISO - No se confirmo carga, continuando...")
            time.sleep(2)
        except Exception as e:
            log(f"Ko-fi ERROR PDF: {e}")
    else:
        log("Ko-fi ERROR: No se encontro PDF.")

    # Desmarcar checkboxes no deseados
    log("Ko-fi: Ajustando checkboxes...")
    driver.execute_script("""
        var labels = document.querySelectorAll('label');
        var textosDes = ['Pay what you want','Limit the quantity','Schedule','Leave a message'];
        labels.forEach(function(label) {
            var txt = label.innerText || '';
            textosDes.forEach(function(des) {
                if (txt.includes(des)) {
                    var cb = label.querySelector('input[type=checkbox]');
                    if (!cb) { var id = label.getAttribute('for'); if (id) cb = document.getElementById(id); }
                    if (cb && cb.checked) cb.click();
                }
            });
        });
    """)
    time.sleep(1)

    # Precio
    log("Ko-fi: Escribiendo precio...")
    try:
        precio_input = wait.until(EC.visibility_of_element_located(
            (By.CSS_SELECTOR, "input[type='number']")))
        precio_input.click()
        driver.execute_script("arguments[0].value = '';", precio_input)
        precio_input.send_keys(datos.get("PRECIO", "10"))
        log("Ko-fi: Precio escrito.")
    except Exception as e:
        log(f"Ko-fi AVISO precio: {e}")

    # Marcar checkbox de copyright
    log("Ko-fi: Aceptando terminos de copyright...")
    try:
        driver.execute_script("""
            var labels = document.querySelectorAll('label');
            labels.forEach(function(label) {
                var txt = label.innerText || '';
                if (txt.includes('I created the original') || txt.includes('copyrighted')) {
                    var cb = label.querySelector('input[type=checkbox]');
                    if (!cb) { var id = label.getAttribute('for'); if (id) cb = document.getElementById(id); }
                    if (cb && !cb.checked) cb.click();
                }
            });
        """)
        time.sleep(1)
        log("Ko-fi: Terminos aceptados.")
    except Exception as e:
        log(f"Ko-fi AVISO terminos: {e}")

    # Boton Save and publish
    log("Ko-fi: Buscando boton Save and publish...")
    btn_save = None
    for xpath in [
        "//button[normalize-space(text())='Save and publish']",
        "//button[contains(text(),'Save and publish')]",
        "//button[contains(text(),'Save and Publish')]",
    ]:
        try:
            btn_save = wait.until(EC.presence_of_element_located((By.XPATH, xpath)))
            log(f"Ko-fi: Boton encontrado: '{btn_save.text}'")
            break
        except:
            continue

    if not btn_save:
        try:
            btn_save = driver.find_element(By.ID, "saveAndPublishButton")
            log("Ko-fi: Boton encontrado por ID.")
        except:
            pass

    if not btn_save:
        try:
            for b in driver.find_elements(By.CSS_SELECTOR, "button"):
                if b.is_displayed() and ("save" in b.text.lower() or "publish" in b.text.lower()):
                    btn_save = b
                    log(f"Ko-fi: Boton: '{b.text}'")
                    break
        except:
            pass

    if btn_save:
        log("Ko-fi: Esperando que el boton este habilitado...")
        for _ in range(15):
            try:
                if not driver.execute_script("return arguments[0].disabled;", btn_save):
                    break
            except:
                break
            time.sleep(1)

        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", btn_save)
        time.sleep(1)
        driver.execute_script("arguments[0].click();", btn_save)
        log("Ko-fi: Clic en Save and publish.")
        time.sleep(6)
    else:
        log("Ko-fi ERROR: No se encontro boton de publicar.")
        return

    # Capturar URL — leer del campo id=directLinkPost del modal
    url_kofi = ""
    try:
        campo_url = WebDriverWait(driver, 8).until(
            EC.presence_of_element_located((By.ID, "directLinkPost")))
        url_kofi = campo_url.get_attribute("value")
        log(f"Ko-fi URL: {url_kofi}")
    except:
        pass

    if not url_kofi:
        url_kofi = driver.current_url
        log(f"Ko-fi URL (pagina): {url_kofi}")

    guardar_url(carpeta, "URL_KOFI", url_kofi)
    log("Ko-fi: Listo.")

# ─────────────────────────────────────────────
#  ITCH.IO
# ─────────────────────────────────────────────
def subir_itch(driver, carpeta, datos, log):
    log("Itch.io: Abriendo pagina...")
    driver.get("https://itch.io/game/new")
    wait = WebDriverWait(driver, 30)
    time.sleep(4)

    log("Itch.io: Escribiendo titulo...")
    titulo = wait.until(EC.presence_of_element_located(
        (By.CSS_SELECTOR, "input[name='game[title]']")))
    titulo.clear()
    titulo.send_keys(datos.get("TITULO", ""))
    time.sleep(2)

    log("Itch.io: Seleccionando Paid...")
    wait.until(EC.element_to_be_clickable(
        (By.CSS_SELECTOR, "button.payment_mode_paid"))).click()
    time.sleep(3)

    log("Itch.io: Escribiendo precio...")
    try:
        # El campo de precio minimo aparece despues de seleccionar Paid
        precio = wait.until(EC.visibility_of_element_located(
            (By.CSS_SELECTOR, "input[name='game[min_price]']")))
        driver.execute_script("arguments[0].style.display='block';", precio)
        precio.clear()
        precio.send_keys(datos.get("PRECIO", "10"))
        log("Itch.io: Precio minimo escrito.")
    except:
        try:
            # Fallback: suggested_price
            precio = driver.find_element(
                By.CSS_SELECTOR, "input[name='game[suggested_price]']")
            driver.execute_script("arguments[0].style.display='block';", precio)
            precio.clear()
            precio.send_keys(datos.get("PRECIO", "10"))
            log("Itch.io: Precio sugerido escrito.")
        except Exception as e:
            log(f"Itch.io AVISO precio: {e}")

    log("Itch.io: Subiendo PDF...")
    pdf = buscar_archivo(carpeta, [".pdf"])
    if pdf:
        try:
            import pyautogui
            btn_upload = wait.until(EC.element_to_be_clickable(
                (By.XPATH, "//button[contains(text(),'Upload files')]")))
            driver.execute_script("arguments[0].scrollIntoView({block:'center'});", btn_upload)
            time.sleep(1)
            btn_upload.click()
            time.sleep(3)
            pyautogui.write(pdf, interval=0.05)
            time.sleep(1)
            pyautogui.press('enter')
            log("Itch.io: PDF enviado via dialogo del sistema.")
            time.sleep(8)
        except Exception as e:
            log(f"Itch.io ERROR PDF: {e}")
    else:
        log("Itch.io ERROR: No se encontro PDF.")

    log("Itch.io: Escribiendo descripcion...")
    try:
        desc_area = wait.until(EC.presence_of_element_located(
            (By.CSS_SELECTOR, "textarea[name='game[description]']")))
        driver.execute_script("arguments[0].style.display='block';", desc_area)
        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", desc_area)
        time.sleep(1)
        desc_area.click()
        desc_area.send_keys(datos.get("DESCRIPCION", ""))
        log("Itch.io: Descripcion escrita.")
    except Exception as e:
        log(f"Itch.io AVISO descripcion: {e}")

    log("Itch.io: Seleccionando Published...")
    try:
        radio_pub = driver.find_element(
            By.CSS_SELECTOR, "input[name='game[published]'][value='published']")
        driver.execute_script("arguments[0].click();", radio_pub)
        log("Itch.io: Visibilidad = Published.")
    except Exception as e:
        log(f"Itch.io AVISO published: {e}")

    log("Itch.io: Guardando...")
    btn_save = wait.until(EC.element_to_be_clickable(
        (By.CSS_SELECTOR, "button.save_btn")))
    driver.execute_script("arguments[0].scrollIntoView({block:'center'});", btn_save)
    time.sleep(1)
    driver.execute_script("arguments[0].click();", btn_save)
    time.sleep(8)

    url = driver.current_url
    log(f"Itch.io URL: {url}")
    guardar_url(carpeta, "URL_ITCH", url)
    log("Itch.io: Listo.")

# ─────────────────────────────────────────────
#  GUMROAD
# ─────────────────────────────────────────────
def subir_gumroad(driver, carpeta, datos, log):
    log("Gumroad: Abriendo pagina de login...")
    driver.get("https://gumroad.com/login")
    wait = WebDriverWait(driver, 120)
    time.sleep(3)

    # Siempre esperar que el usuario inicie sesion manualmente
    if "login" in driver.current_url:
        log(">>> ACCION REQUERIDA: Inicia sesion en Gumroad en el navegador.")
        log(">>> Tienes 2 minutos. El proceso continuara automaticamente.")
        for _ in range(120):
            time.sleep(1)
            if "login" not in driver.current_url:
                log("Gumroad: Sesion detectada, continuando...")
                time.sleep(2)
                break
        else:
            log("Gumroad ERROR: No se inicio sesion a tiempo. Saltando Gumroad.")
            return

    # Navegar a nuevo producto
    driver.get("https://gumroad.com/products/new")
    time.sleep(4)

    # Verificar que sigue con sesion activa
    if "login" in driver.current_url:
        log("Gumroad ERROR: Sesion perdida al navegar. Saltando Gumroad.")
        return

    # --- PASO 1: Nombre, tipo y precio ---
    log("Gumroad: Escribiendo nombre...")
    nombre = wait.until(EC.visibility_of_element_located(
        (By.CSS_SELECTOR, "input[type='text']")))
    nombre.clear()
    nombre.send_keys(datos.get("TITULO", ""))

    log("Gumroad: Seleccionando E-book...")
    try:
        ebook_btn = wait.until(EC.element_to_be_clickable(
            (By.XPATH, "//button[.//h4[contains(text(),'E-book')] or contains(text(),'E-book')]")))
        driver.execute_script("arguments[0].click();", ebook_btn)
        log("Gumroad: E-book seleccionado.")
        time.sleep(1)
    except Exception as e:
        log(f"Gumroad AVISO tipo: {e}")

    log("Gumroad: Escribiendo precio...")
    try:
        # El precio es el segundo input de texto visible
        inputs_text = driver.find_elements(By.CSS_SELECTOR, "input[type='text']")
        precio_input = None
        for inp in inputs_text:
            if inp.is_displayed() and inp != nombre:
                precio_input = inp
                break
        if precio_input:
            precio_input.clear()
            precio_input.send_keys(datos.get("PRECIO", "10"))
            log("Gumroad: Precio escrito.")
    except Exception as e:
        log(f"Gumroad AVISO precio: {e}")

    log("Gumroad: Clic en Next: Customize...")
    btn_next = wait.until(EC.element_to_be_clickable(
        (By.XPATH, "//button[contains(text(),'Next')]")))
    driver.execute_script("arguments[0].click();", btn_next)
    time.sleep(5)

    # --- PASO 2: Descripcion, portada, guardar ---
    log("Gumroad: Esperando pagina de edicion...")
    wait.until(EC.url_contains("/edit"))
    time.sleep(3)

    log("Gumroad: Escribiendo descripcion...")
    try:
        desc = wait.until(EC.element_to_be_clickable(
            (By.CSS_SELECTOR, "div.ProseMirror[contenteditable='true']")))
        desc.click()
        time.sleep(1)
        desc.send_keys(datos.get("DESCRIPCION", ""))
        log("Gumroad: Descripcion escrita.")
    except Exception as e:
        log(f"Gumroad AVISO descripcion: {e}")

    log("Gumroad: Subiendo portada (Cover)...")
    portada = buscar_archivo(carpeta, [".jpg", ".jpeg", ".png"])
    if portada:
        try:
            # Recargar pagina actual para resetear cualquier foco del editor
            url_actual = driver.current_url
            driver.get(url_actual)
            time.sleep(3)

            # Buscar el input de Cover navegando directamente desde el texto "Cover"
            input_cover = driver.execute_script("""
                var heading = null;
                var headings = document.querySelectorAll('h2, h3');
                for (var i = 0; i < headings.length; i++) {
                    if (headings[i].innerText.trim() === 'Cover') {
                        heading = headings[i];
                        break;
                    }
                }
                if (!heading) return null;
                // Buscar en el siguiente sibling/seccion
                var section = heading.closest('section') || heading.parentElement.parentElement;
                if (!section) return null;
                var inputs = section.querySelectorAll('input[type=file]');
                for (var j = 0; j < inputs.length; j++) {
                    var accept = inputs[j].accept || '';
                    if (accept.includes('jpeg')) return inputs[j];
                }
                return null;
            """)

            if input_cover:
                driver.execute_script("arguments[0].style.display='block';", input_cover)
                input_cover.send_keys(portada)
                log("Gumroad: Portada enviada al Cover (via heading).")
                time.sleep(4)
            else:
                log("Gumroad AVISO: No se encontro input de Cover via heading.")
        except Exception as e:
            log(f"Gumroad AVISO portada: {e}")

    log("Gumroad: Activando VAT e-publication...")
    try:
        driver.execute_script("""
            var labels = document.querySelectorAll('label');
            for (var i = 0; i < labels.length; i++) {
                var txt = labels[i].innerText || '';
                if (txt.includes('e-publication') || txt.includes('VAT')) {
                    var toggle = labels[i].querySelector('input[type=checkbox], button[role=switch]');
                    if (!toggle) toggle = labels[i].previousElementSibling;
                    if (toggle) {
                        var checked = toggle.checked || toggle.getAttribute('aria-checked') === 'true';
                        if (!checked) toggle.click();
                    }
                }
            }
        """)
        time.sleep(1)
        log("Gumroad: VAT activado.")
    except Exception as e:
        log(f"Gumroad AVISO VAT: {e}")

    log("Gumroad: Guardando producto (Save and continue)...")
    try:
        btn_save = wait.until(EC.element_to_be_clickable(
            (By.XPATH, "//button[contains(text(),'Save and continue')]")))
        driver.execute_script("arguments[0].click();", btn_save)
        time.sleep(5)
    except Exception as e:
        log(f"Gumroad AVISO save: {e}")

    # --- PASO 3: Subir PDF en tab Content ---
    log("Gumroad: Abriendo tab Content...")
    try:
        wait.until(EC.url_contains("/edit"))
        # Navegar al tab Content
        tab_content = wait.until(EC.element_to_be_clickable(
            (By.XPATH, "//a[contains(text(),'Content')] | //button[contains(text(),'Content')]")))
        driver.execute_script("arguments[0].click();", tab_content)
        time.sleep(3)
    except Exception as e:
        log(f"Gumroad AVISO tab content: {e}")
        # Intentar navegar directo a la URL de content
        url_edit = driver.current_url
        if "/edit" in url_edit and "/content" not in url_edit:
            driver.get(url_edit.replace("/edit", "/edit/content"))
            time.sleep(4)

    log("Gumroad: Subiendo PDF...")
    pdf = buscar_archivo(carpeta, [".pdf"])
    if pdf:
        try:
            # En tab Content hay exactamente 1 input[type=file] con accept vacio
            inputs_file = driver.find_elements(By.CSS_SELECTOR, "input[type=file]")
            log(f"Gumroad: {len(inputs_file)} inputs file en Content.")
            input_pdf = None
            for inp in inputs_file:
                accept = inp.get_attribute("accept") or ""
                if accept == "":
                    input_pdf = inp
                    break
            if not input_pdf and inputs_file:
                input_pdf = inputs_file[0]
            if input_pdf:
                driver.execute_script("arguments[0].style.display='block';", input_pdf)
                input_pdf.send_keys(pdf)
                log("Gumroad: PDF enviado.")
                time.sleep(8)
            else:
                log("Gumroad AVISO: No se encontro input para PDF.")
        except Exception as e:
            log(f"Gumroad AVISO PDF: {e}")
    else:
        log("Gumroad ERROR: No se encontro PDF.")

        log("Gumroad: Publicando...")
    try:
        btn_pub = wait.until(EC.element_to_be_clickable(
            (By.XPATH, "//button[contains(text(),'Publish and continue')]")))
        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", btn_pub)
        time.sleep(1)
        driver.execute_script("arguments[0].click();", btn_pub)
        time.sleep(5)
    except Exception as e:
        log(f"Gumroad AVISO publicar: {e}")

    # Capturar URL del producto
    url = driver.current_url
    # Extraer la URL publica del producto si es posible
    try:
        url_publica = driver.find_element(
            By.XPATH, "//a[contains(@href,'gumroad.com/l/')]")
        url = url_publica.get_attribute("href")
    except:
        pass
    log(f"Gumroad URL: {url}")
    guardar_url(carpeta, "URL_GUMROAD", url)
    log("Gumroad: Listo.")

# ─────────────────────────────────────────────
#  INTERFAZ TKINTER
# ─────────────────────────────────────────────
class App:
    def __init__(self, root):
        self.root = root
        self.root.title("Subidor Multiplataforma")
        self.root.geometry("420x500")
        self.carpeta = ""

        tk.Button(root, text="Seleccionar carpeta del manual",
                  command=self.elegir_carpeta,
                  font=("Arial", 11)).pack(pady=15)

        self.lbl_carpeta = tk.Label(root, text="Ninguna carpeta seleccionada",
                                    wraplength=380, fg="gray")
        self.lbl_carpeta.pack()

        tk.Label(root, text="Plataformas:", font=("Arial", 11, "bold")).pack(pady=(15, 5))

        self.var_gumroad = tk.BooleanVar()
        self.var_payhip  = tk.BooleanVar(value=True)
        self.var_kofi    = tk.BooleanVar()
        self.var_itch    = tk.BooleanVar()

        tk.Checkbutton(root, text="Gumroad",  variable=self.var_gumroad, font=("Arial", 11)).pack()
        tk.Checkbutton(root, text="Payhip",   variable=self.var_payhip,  font=("Arial", 11)).pack()
        tk.Checkbutton(root, text="Ko-fi",    variable=self.var_kofi,    font=("Arial", 11)).pack()
        tk.Checkbutton(root, text="Itch.io",  variable=self.var_itch,    font=("Arial", 11)).pack()

        tk.Button(root, text="SUBIR",
                  command=self.subir,
                  font=("Arial", 13, "bold"),
                  bg="#2ecc71", fg="white",
                  width=20, height=2).pack(pady=20)

        self.log_box = tk.Text(root, height=8, state="disabled", font=("Courier", 9))
        self.log_box.pack(fill="x", padx=10, pady=(0, 10))

    def elegir_carpeta(self):
        carpeta = filedialog.askdirectory(title="Selecciona la carpeta del manual")
        if carpeta:
            self.carpeta = carpeta
            self.lbl_carpeta.config(text=carpeta, fg="black")

    def log(self, msg):
        self.log_box.config(state="normal")
        self.log_box.insert("end", msg + "\n")
        self.log_box.see("end")
        self.log_box.config(state="disabled")
        self.root.update()

    def subir(self):
        if not self.carpeta:
            messagebox.showerror("Error", "Selecciona una carpeta primero.")
            return
        if not any([self.var_payhip.get(), self.var_gumroad.get(),
                    self.var_kofi.get(), self.var_itch.get()]):
            messagebox.showerror("Error", "Selecciona al menos una plataforma.")
            return
        self.log("Iniciando...")
        threading.Thread(target=self.proceso, daemon=True).start()

    def proceso(self):
        driver = None
        perfil_temp = None
        try:
            datos = leer_descripcion(self.carpeta)
            self.log("Iniciando Firefox...")
            driver, perfil_temp = crear_driver()

            if self.var_payhip.get():
                subir_payhip(driver, self.carpeta, datos, self.log)
            if self.var_kofi.get():
                subir_kofi(driver, self.carpeta, datos, self.log)
            if self.var_itch.get():
                subir_itch(driver, self.carpeta, datos, self.log)
            if self.var_gumroad.get():
                subir_gumroad(driver, self.carpeta, datos, self.log)

        except Exception as e:
            self.log(f"ERROR: {e}")
        finally:
            self.log("Proceso terminado. Revisa el navegador y cierra cuando quieras.")

if __name__ == "__main__":
    root = tk.Tk()
    app = App(root)
    root.mainloop()