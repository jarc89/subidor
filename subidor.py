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
import pyautogui
import subprocess

def leer_descripcion(carpeta):
    ruta = os.path.join(carpeta, "descripcion.txt")
    datos = {}
    with open(ruta, encoding="utf-8") as f:
        contenido = f.read()
    for linea in contenido.splitlines():
        if "=" in linea:
            clave, _, valor = linea.partition("=")
            datos[clave.strip()] = valor.strip()
    return datos

def guardar_url(carpeta, clave, url):
    ruta = os.path.join(carpeta, "descripcion.txt")
    with open(ruta, encoding="utf-8") as f:
        contenido = f.read()
    nuevas_lineas = []
    for linea in contenido.splitlines():
        if linea.startswith(f"{clave}="):
            nuevas_lineas.append(f"{clave}={url}")
        else:
            nuevas_lineas.append(linea)
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

def subir_archivo_dialogo(ruta_archivo):
    time.sleep(3)
    # Copiar ruta al portapapeles
    subprocess.run('clip', input=ruta_archivo.encode('utf-8'), shell=True)
    time.sleep(1)
    # Escribir ruta en campo nombre de archivo
    pyautogui.hotkey('alt', 'd')
    time.sleep(0.5)
    pyautogui.hotkey('ctrl', 'a')
    time.sleep(0.3)
    pyautogui.hotkey('ctrl', 'v')
    time.sleep(0.5)
    pyautogui.press('enter')
    time.sleep(3)

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

    url_actual = driver.current_url
    log(f"Payhip URL: {url_actual}")
    guardar_url(carpeta, "URL_PAYHIP", url_actual)

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

    log("Ko-fi: Escribiendo descripcion...")
    desc = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "textarea[placeholder='Share your listing']")))
    desc.clear()
    desc.send_keys(datos.get("DESCRIPCION", ""))

    portada = buscar_archivo(carpeta, [".jpg", ".jpeg", ".png"])
    if portada:
        log("Ko-fi: Subiendo portada...")
        inputs = driver.find_elements(By.CSS_SELECTOR, "input[type='file']")
        if inputs:
            inputs[0].send_keys(portada)
        time.sleep(4)

    log("Ko-fi: Subiendo PDF en Assets...")
pdf = buscar_archivo(carpeta, [".pdf"])
if pdf:
    try:
        # Crear input file oculto y enviarlo directamente
        driver.execute_script("""
            var input = document.createElement('input');
            input.type = 'file';
            input.accept = '.pdf';
            input.style.position = 'fixed';
            input.style.top = '0';
            input.style.left = '0';
            input.style.opacity = '0.01';
            input.style.zIndex = '99999';
            document.body.appendChild(input);
            window._kofi_file_input = input;
        """)
        time.sleep(1)
        file_input = driver.find_element(By.CSS_SELECTOR, "input[accept='.pdf']")
        file_input.send_keys(pdf)
        time.sleep(5)
    except Exception as e:
        log(f"Ko-fi AVISO PDF: {e}")

    log("Ko-fi: Escribiendo precio...")
    precio_input = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='number']")))
    precio_input.clear()
    precio_input.send_keys(datos.get("PRECIO", "10"))

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

    log("Ko-fi: Guardando...")
    btn_save = wait.until(EC.element_to_be_clickable((By.ID, "saveAndPublishButton")))
    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", btn_save)
    time.sleep(1)
    driver.execute_script("arguments[0].click();", btn_save)
    time.sleep(6)

    url_actual = driver.current_url
    log(f"Ko-fi URL: {url_actual}")
    guardar_url(carpeta, "URL_KOFI", url_actual)

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

    url_actual = driver.current_url
    log(f"Itch.io URL: {url_actual}")
    guardar_url(carpeta, "URL_ITCH", url_actual)

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

    url_actual = driver.current_url
    log(f"Gumroad URL: {url_actual}")
    guardar_url(carpeta, "URL_GUMROAD", url_actual)

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
            if driver:
                driver.quit()
            if perfil_temp and os.path.exists(perfil_temp):
                shutil.rmtree(perfil_temp, ignore_errors=True)
            self.log("Proceso terminado.")

if __name__ == "__main__":
    root = tk.Tk()
    app = App(root)
    root.mainloop()