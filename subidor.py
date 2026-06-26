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
    # Claves que marcan fin de DESCRIPCION si aparecen solas en una linea
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
            # Si es una clave conocida, cerramos DESCRIPCION y procesamos normal
            if clave in CLAVES_CONOCIDAS:
                en_descripcion = False
                if clave == "DESCRIPCION":
                    datos[clave] = valor.strip()
                    en_descripcion = True
                else:
                    datos[clave] = valor.strip()
                continue
        # Si estamos acumulando descripcion, agregamos la linea
        if en_descripcion:
            datos["DESCRIPCION"] += "\n" + linea
    return datos

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
#  PAYHIP  (confirmado funcionando)
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
    log("Payhip: Listo. Pagina disponible en el navegador.")

# ─────────────────────────────────────────────
#  KO-FI
# ─────────────────────────────────────────────
def subir_kofi(driver, carpeta, datos, log):
    log("Ko-fi: Abriendo pagina...")
    driver.get("https://ko-fi.com/shop/settings?productType=0")
    wait = WebDriverWait(driver, 30)
    time.sleep(5)

    log("Ko-fi: Abriendo modal de producto...")
    btn_add = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(text(),'Add product')]")))
    driver.execute_script("arguments[0].click();", btn_add)
    time.sleep(3)

    log("Ko-fi: Escribiendo nombre...")
    nombre = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "input[placeholder='e.g. Comic PDF']")))
    nombre.clear()
    nombre.send_keys(datos.get("TITULO", ""))

    log("Ko-fi: Siguiente paso...")
    wait.until(EC.presence_of_element_located((By.ID, "shopModalNextStep")))
    driver.execute_script("document.getElementById('shopModalNextStep').click();")
    time.sleep(4)

    log("Ko-fi: Esperando formulario completo...")
    wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "textarea[placeholder='Share your listing']")))
    time.sleep(2)

    log("Ko-fi: Escribiendo descripcion...")
    desc = driver.find_element(By.CSS_SELECTOR, "textarea[placeholder='Share your listing']")
    desc.clear()
    desc.send_keys(datos.get("DESCRIPCION", ""))

    # --- Portada ---
    portada = buscar_archivo(carpeta, [".jpg", ".jpeg", ".png"])
    if portada:
        log("Ko-fi: Subiendo portada...")
        try:
            inputs = driver.find_elements(By.CSS_SELECTOR, "input.dz-hidden-input")
            if inputs:
                inputs[0].send_keys(portada)
                time.sleep(4)
        except Exception as e:
            log(f"Ko-fi AVISO portada: {e}")

    # --- PDF Asset ---
    pdf = buscar_archivo(carpeta, [".pdf"])
    if pdf:
        log("Ko-fi: Subiendo PDF en Assets...")
        try:
            inputs = driver.find_elements(By.CSS_SELECTOR, "input.dz-hidden-input")
            if len(inputs) > 1:
                inputs[1].send_keys(pdf)
                log("Ko-fi: PDF enviado al input de Assets.")
            elif len(inputs) == 1:
                log("Ko-fi: Solo 1 input dz, intentando via input[type=file]...")
                todos = driver.find_elements(By.CSS_SELECTOR, "input[type='file']")
                for inp in todos:
                    clase = inp.get_attribute("class") or ""
                    if "dz" in clase:
                        inp.send_keys(pdf)
                        log("Ko-fi: PDF enviado via input[type=file] dz.")
                        break

            log("Ko-fi: Esperando que el PDF termine de cargar...")
            cargado = False
            for _ in range(25):
                time.sleep(1)
                try:
                    exitos = driver.find_elements(By.CSS_SELECTOR, ".dz-success, .dz-complete")
                    if exitos:
                        log("Ko-fi: PDF cargado (dz-success detectado).")
                        cargado = True
                        break
                    nombres = driver.find_elements(By.CSS_SELECTOR, ".dz-filename span")
                    if nombres and any(n.text.strip() for n in nombres):
                        log(f"Ko-fi: PDF cargado ({nombres[0].text.strip()}).")
                        cargado = True
                        break
                    btns = driver.find_elements(By.ID, "saveAndPublishButton")
                    if btns:
                        disabled = driver.execute_script("return arguments[0].disabled;", btns[0])
                        if not disabled:
                            log("Ko-fi: Boton Save habilitado, PDF listo.")
                            cargado = True
                            break
                except:
                    pass
            if not cargado:
                log("Ko-fi: AVISO - No se confirmo carga del PDF, continuando de todas formas...")
            time.sleep(2)
        except Exception as e:
            log(f"Ko-fi ERROR PDF: {e}")
    else:
        log("Ko-fi ERROR: No se encontro PDF.")

    # --- Precio ---
    log("Ko-fi: Escribiendo precio...")
    try:
        precio_input = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='number']")))
        precio_input.clear()
        precio_input.send_keys(datos.get("PRECIO", "10"))
    except Exception as e:
        log(f"Ko-fi AVISO precio: {e}")

    # --- Checkboxes de terminos ---
    log("Ko-fi: Aceptando terminos...")
    driver.execute_script("""
        var checkboxes = document.querySelectorAll('input[type=checkbox]');
        checkboxes.forEach(function(cb) {
            if (cb.id !== 'darkThemeToggle' && !cb.checked) {
                cb.click();
            }
        });
    """)
    time.sleep(1)

    # --- Boton Save and Publish (3 estrategias) ---
    log("Ko-fi: Buscando boton Save and Publish...")
    btn_save = None

    try:
        btn_save = wait.until(EC.presence_of_element_located((By.ID, "saveAndPublishButton")))
        log("Ko-fi: Boton encontrado por ID.")
    except:
        pass

    if not btn_save:
        try:
            btn_save = driver.find_element(By.XPATH,
                "//button[contains(translate(text(),'abcdefghijklmnopqrstuvwxyz','ABCDEFGHIJKLMNOPQRSTUVWXYZ'),'SAVE')]")
            log(f"Ko-fi: Boton encontrado por texto: '{btn_save.text}'")
        except:
            pass

    if not btn_save:
        try:
            botones = driver.find_elements(By.CSS_SELECTOR, "button[type='submit']")
            for b in botones:
                if b.is_displayed():
                    btn_save = b
                    log(f"Ko-fi: Boton submit encontrado: '{b.text}'")
                    break
        except:
            pass

    if btn_save:
        log("Ko-fi: Esperando que el boton este habilitado...")
        for _ in range(15):
            disabled = driver.execute_script("return arguments[0].disabled;", btn_save)
            if not disabled:
                break
            time.sleep(1)
        else:
            log("Ko-fi: Forzando habilitacion del boton...")
            driver.execute_script("arguments[0].disabled = false;", btn_save)
            time.sleep(1)

        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", btn_save)
        time.sleep(1)
        driver.execute_script("arguments[0].click();", btn_save)
        log("Ko-fi: Clic en Save realizado.")
        time.sleep(6)
    else:
        log("Ko-fi ERROR: No se encontro el boton de guardar.")

    log("Ko-fi: Listo. Pagina disponible en el navegador.")

# ─────────────────────────────────────────────
#  ITCH.IO  (pendiente de prueba)
# ─────────────────────────────────────────────
def subir_itch(driver, carpeta, datos, log):
    log("Itch.io: Abriendo pagina...")
    driver.get("https://itch.io/game/new")
    wait = WebDriverWait(driver, 30)
    time.sleep(4)

    log("Itch.io: Escribiendo titulo...")
    titulo = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "input[name='game[title]']")))
    titulo.clear()
    titulo.send_keys(datos.get("TITULO", ""))
    time.sleep(2)

    log("Itch.io: Seleccionando tipo libro...")
    kind = driver.find_element(By.CSS_SELECTOR, "select[name='game[classification]']")
    Select(kind).select_by_value("book")

    tipo = driver.find_element(By.CSS_SELECTOR, "select[name='game[kind]']")
    Select(tipo).select_by_value("downloadable")

    log("Itch.io: Seleccionando Paid...")
    driver.find_element(By.CSS_SELECTOR, "input[value='paid']").click()
    time.sleep(2)

    log("Itch.io: Escribiendo precio...")
    precio = driver.find_element(By.CSS_SELECTOR, "input[name='game[price]']")
    precio.clear()
    precio.send_keys(datos.get("PRECIO", "10"))

    log("Itch.io: Subiendo PDF...")
    pdf = buscar_archivo(carpeta, [".pdf"])
    if pdf:
        btn_upload = driver.find_element(By.CSS_SELECTOR, "input.upload-btn[type='file']")
        btn_upload.send_keys(pdf)
        time.sleep(8)

    log("Itch.io: Escribiendo descripcion...")
    desc = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.CodeMirror")))
    desc.click()
    time.sleep(1)
    area = driver.find_element(By.CSS_SELECTOR, "div.CodeMirror textarea")
    area.send_keys(datos.get("DESCRIPCION", ""))

    log("Itch.io: Seleccionando Public...")
    driver.find_element(By.CSS_SELECTOR, "input[value='public']").click()

    log("Itch.io: Guardando...")
    btn = driver.find_element(By.CSS_SELECTOR, "button.save_btn")
    btn.click()
    time.sleep(8)
    log("Itch.io: Listo. Pagina disponible en el navegador.")

# ─────────────────────────────────────────────
#  GUMROAD  (pendiente de prueba)
# ─────────────────────────────────────────────
def subir_gumroad(driver, carpeta, datos, log):
    log("Gumroad: Abriendo pagina...")
    driver.get("https://gumroad.com/products/new")
    wait = WebDriverWait(driver, 30)
    time.sleep(4)

    log("Gumroad: Escribiendo nombre...")
    nombre = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "input[name='name']")))
    nombre.clear()
    nombre.send_keys(datos.get("TITULO", ""))

    log("Gumroad: Seleccionando E-book...")
    try:
        ebook = driver.find_element(By.XPATH, "//div[contains(text(),'E-book')]")
        ebook.click()
    except:
        pass

    log("Gumroad: Escribiendo precio...")
    precio = driver.find_element(By.CSS_SELECTOR, "input[name='price']")
    precio.clear()
    precio.send_keys(datos.get("PRECIO", "10"))

    log("Gumroad: Siguiente paso...")
    btn_next = driver.find_element(By.XPATH, "//button[contains(text(),'Next')]")
    btn_next.click()
    time.sleep(5)

    log("Gumroad: Escribiendo descripcion...")
    desc = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "div[contenteditable='true']")))
    desc.click()
    desc.send_keys(datos.get("DESCRIPCION", ""))

    portada = buscar_archivo(carpeta, [".jpg", ".jpeg", ".png"])
    if portada:
        log("Gumroad: Subiendo portada...")
        inputs = driver.find_elements(By.CSS_SELECTOR, "input[type='file']")
        if inputs:
            inputs[0].send_keys(portada)
        time.sleep(4)

    log("Gumroad: Guardando producto...")
    btn_save = driver.find_element(By.XPATH, "//button[contains(text(),'Save and continue')]")
    btn_save.click()
    time.sleep(5)

    log("Gumroad: Subiendo PDF...")
    try:
        pdf = buscar_archivo(carpeta, [".pdf"])
        if pdf:
            input_file = driver.find_element(By.CSS_SELECTOR, "input[type='file']")
            input_file.send_keys(pdf)
            time.sleep(8)
    except Exception as e:
        log(f"Gumroad AVISO PDF: {e}")

    log("Gumroad: Publicando...")
    try:
        btn_pub = driver.find_element(By.XPATH, "//button[contains(text(),'Publish and continue')]")
        btn_pub.click()
        time.sleep(5)
    except:
        pass

    log("Gumroad: Listo. Pagina disponible en el navegador.")

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

        self.lbl_carpeta = tk.Label(root,
                                    text="Ninguna carpeta seleccionada",
                                    wraplength=380, fg="gray")
        self.lbl_carpeta.pack()

        tk.Label(root, text="Plataformas:",
                 font=("Arial", 11, "bold")).pack(pady=(15, 5))

        self.var_gumroad = tk.BooleanVar()
        self.var_payhip  = tk.BooleanVar(value=True)
        self.var_kofi    = tk.BooleanVar()
        self.var_itch    = tk.BooleanVar()

        tk.Checkbutton(root, text="Gumroad",
                       variable=self.var_gumroad, font=("Arial", 11)).pack()
        tk.Checkbutton(root, text="Payhip",
                       variable=self.var_payhip,  font=("Arial", 11)).pack()
        tk.Checkbutton(root, text="Ko-fi",
                       variable=self.var_kofi,    font=("Arial", 11)).pack()
        tk.Checkbutton(root, text="Itch.io",
                       variable=self.var_itch,    font=("Arial", 11)).pack()

        tk.Button(root, text="SUBIR",
                  command=self.subir,
                  font=("Arial", 13, "bold"),
                  bg="#2ecc71", fg="white",
                  width=20, height=2).pack(pady=20)

        self.log_box = tk.Text(root, height=8,
                               state="disabled",
                               font=("Courier", 9))
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
        perfil_temp = None
        driver = None
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
            # NO cerramos el driver - el navegador queda abierto para revision
            self.log("Proceso terminado. Revisa el navegador y cierra cuando quieras.")

if __name__ == "__main__":
    root = tk.Tk()
    app = App(root)
    root.mainloop()