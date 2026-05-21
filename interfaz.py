# -*- coding: utf-8 -*-
"""
interfaz.py — Interfaz grafica para mejorar videos e imagenes con IA.

Uso:
    python interfaz.py
"""

import os
import sys
import json
import threading
import subprocess
import shutil
import customtkinter as ctk
from tkinter import filedialog, messagebox
from PIL import Image, ImageTk

# ─── Config ─────────────────────────────────────────────
BASE        = os.path.dirname(os.path.abspath(__file__))
ESRGAN_EXE  = os.path.join(BASE, "realesrgan", "realesrgan-ncnn-vulkan.exe")
ESRGAN_DIR  = os.path.join(BASE, "realesrgan")

EXTENSIONES_VIDEO  = (".mp4", ".mov", ".avi", ".mkv", ".webm")
EXTENSIONES_IMAGEN = (".jpg", ".jpeg", ".png", ".bmp", ".webp")

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


# ─── Ventana principal ───────────────────────────────────

class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("AEGS — Mejorador de Video e Imagen con IA")
        self.geometry("820x680")
        self.resizable(False, False)

        self.archivo_seleccionado = None
        self.procesando = False

        self._construir_ui()

    # ── UI ──────────────────────────────────────────────

    def _construir_ui(self):
        # Titulo
        ctk.CTkLabel(
            self, text="Mejorador de Video e Imagen con IA",
            font=ctk.CTkFont(size=22, weight="bold")
        ).pack(pady=(20, 4))

        ctk.CTkLabel(
            self, text="Selecciona un archivo y elige las mejoras que quieres aplicar",
            font=ctk.CTkFont(size=13), text_color="gray"
        ).pack(pady=(0, 16))

        # ── Zona de archivo ──────────────────────────────
        self.frame_archivo = ctk.CTkFrame(self, height=130, corner_radius=12)
        self.frame_archivo.pack(fill="x", padx=30, pady=(0, 16))
        self.frame_archivo.pack_propagate(False)

        self.lbl_archivo = ctk.CTkLabel(
            self.frame_archivo,
            text="Ningun archivo seleccionado\nHaz clic en 'Seleccionar archivo' para empezar",
            font=ctk.CTkFont(size=13), text_color="gray",
            justify="center"
        )
        self.lbl_archivo.pack(expand=True)

        ctk.CTkButton(
            self.frame_archivo,
            text="Seleccionar archivo (video o imagen)",
            command=self._seleccionar_archivo,
            width=280, height=36,
            font=ctk.CTkFont(size=13)
        ).pack(pady=(0, 12))

        # ── Opciones en dos columnas ─────────────────────
        frame_opciones = ctk.CTkFrame(self, corner_radius=12)
        frame_opciones.pack(fill="x", padx=30, pady=(0, 16))

        ctk.CTkLabel(
            frame_opciones, text="Opciones de mejora",
            font=ctk.CTkFont(size=15, weight="bold")
        ).grid(row=0, column=0, columnspan=4, pady=(12, 8), padx=20, sticky="w")

        # Columna izquierda — mejoras generales
        col_izq = ctk.CTkFrame(frame_opciones, fg_color="transparent")
        col_izq.grid(row=1, column=0, columnspan=2, padx=20, pady=(0, 12), sticky="nw")

        ctk.CTkLabel(col_izq, text="Mejoras generales",
                     font=ctk.CTkFont(size=13, weight="bold"),
                     text_color="#4EA8DE").pack(anchor="w", pady=(0, 6))

        self.var_silencios  = ctk.BooleanVar(value=True)
        self.var_color      = ctk.BooleanVar(value=True)
        self.var_fades      = ctk.BooleanVar(value=True)
        self.var_muletillas = ctk.BooleanVar(value=False)

        ctk.CTkCheckBox(col_izq, text="Eliminar silencios automaticamente",
                        variable=self.var_silencios).pack(anchor="w", pady=3)
        ctk.CTkCheckBox(col_izq, text="Color grading cinematografico",
                        variable=self.var_color).pack(anchor="w", pady=3)
        ctk.CTkCheckBox(col_izq, text="Fades de audio (30ms)",
                        variable=self.var_fades).pack(anchor="w", pady=3)
        ctk.CTkCheckBox(col_izq, text="Eliminar muletillas (umm, eh...)",
                        variable=self.var_muletillas).pack(anchor="w", pady=3)

        # Estilo de color
        frame_estilo = ctk.CTkFrame(col_izq, fg_color="transparent")
        frame_estilo.pack(anchor="w", pady=(8, 0))
        ctk.CTkLabel(frame_estilo, text="Estilo color:").pack(side="left", padx=(0, 8))
        self.estilo_color = ctk.CTkOptionMenu(
            frame_estilo,
            values=["cinematico", "calido", "neutro"],
            width=130
        )
        self.estilo_color.pack(side="left")

        # Columna derecha — Super resolución IA
        col_der = ctk.CTkFrame(frame_opciones, fg_color="transparent")
        col_der.grid(row=1, column=2, columnspan=2, padx=20, pady=(0, 12), sticky="nw")

        ctk.CTkLabel(col_der, text="Super resolucion con IA (Real-ESRGAN)",
                     font=ctk.CTkFont(size=13, weight="bold"),
                     text_color="#4EA8DE").pack(anchor="w", pady=(0, 6))

        self.var_esrgan = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(col_der, text="Mejorar calidad con IA (x4)\n(lento pero brutal resultado)",
                        variable=self.var_esrgan,
                        onvalue=True, offvalue=False).pack(anchor="w", pady=3)

        frame_modelo = ctk.CTkFrame(col_der, fg_color="transparent")
        frame_modelo.pack(anchor="w", pady=(10, 0))
        ctk.CTkLabel(frame_modelo, text="Modelo:").pack(side="left", padx=(0, 8))
        self.modelo_esrgan = ctk.CTkOptionMenu(
            frame_modelo,
            values=["realesrgan-x4plus", "realesrgan-x4plus-anime", "realesrnet-x4plus"],
            width=200
        )
        self.modelo_esrgan.pack(side="left")

        ctk.CTkLabel(col_der,
                     text="realesrgan-x4plus      = fotos reales\n"
                          "realesrgan-x4plus-anime = dibujos/anime\n"
                          "realesrnet-x4plus       = mas rapido",
                     font=ctk.CTkFont(size=11), text_color="gray",
                     justify="left").pack(anchor="w", pady=(8, 0))

        # ── Barra de progreso y estado ───────────────────
        frame_progreso = ctk.CTkFrame(self, corner_radius=12)
        frame_progreso.pack(fill="x", padx=30, pady=(0, 16))

        self.lbl_estado = ctk.CTkLabel(
            frame_progreso, text="Listo para procesar",
            font=ctk.CTkFont(size=13)
        )
        self.lbl_estado.pack(pady=(12, 4))

        self.barra = ctk.CTkProgressBar(frame_progreso, width=700)
        self.barra.pack(pady=(0, 12))
        self.barra.set(0)

        # ── Boton procesar ───────────────────────────────
        self.btn_procesar = ctk.CTkButton(
            self,
            text="PROCESAR",
            command=self._procesar,
            width=300, height=48,
            font=ctk.CTkFont(size=16, weight="bold"),
            fg_color="#1f6aa5", hover_color="#1a5a8f"
        )
        self.btn_procesar.pack(pady=(0, 10))

        ctk.CTkButton(
            self,
            text="Abrir carpeta de salida",
            command=self._abrir_carpeta_salida,
            width=200, height=32,
            fg_color="transparent", border_width=1,
            font=ctk.CTkFont(size=12)
        ).pack()

    # ── Logica ──────────────────────────────────────────

    def _seleccionar_archivo(self):
        ruta = filedialog.askopenfilename(
            title="Seleccionar video o imagen",
            filetypes=[
                ("Videos e imagenes",
                 "*.mp4 *.mov *.avi *.mkv *.webm *.jpg *.jpeg *.png *.bmp *.webp"),
                ("Videos", "*.mp4 *.mov *.avi *.mkv *.webm"),
                ("Imagenes", "*.jpg *.jpeg *.png *.bmp *.webp"),
                ("Todos los archivos", "*.*"),
            ]
        )
        if not ruta:
            return

        self.archivo_seleccionado = ruta
        nombre = os.path.basename(ruta)
        ext    = os.path.splitext(ruta)[1].lower()
        tipo   = "VIDEO" if ext in EXTENSIONES_VIDEO else "IMAGEN"
        tam    = os.path.getsize(ruta) / (1024 * 1024)

        self.lbl_archivo.configure(
            text=f"{tipo}: {nombre}\nTamano: {tam:.1f} MB  |  Ruta: {ruta}",
            text_color="white"
        )
        self.lbl_estado.configure(text="Archivo cargado. Elige las mejoras y haz clic en PROCESAR.")
        self.barra.set(0)

    def _procesar(self):
        if self.procesando:
            return
        if not self.archivo_seleccionado:
            messagebox.showwarning("Aviso", "Primero selecciona un archivo.")
            return

        ext  = os.path.splitext(self.archivo_seleccionado)[1].lower()
        tipo = "video" if ext in EXTENSIONES_VIDEO else "imagen"

        config = {
            "tipo":               tipo,
            "cortar_silencios":   self.var_silencios.get(),
            "color_grading":      self.var_color.get(),
            "estilo_color":       self.estilo_color.get(),
            "audio_fades":        self.var_fades.get(),
            "eliminar_muletillas":self.var_muletillas.get(),
            "esrgan":             self.var_esrgan.get(),
            "modelo_esrgan":      self.modelo_esrgan.get(),
        }

        self.procesando = True
        self.btn_procesar.configure(state="disabled", text="Procesando...")
        self.barra.set(0)

        hilo = threading.Thread(
            target=self._hilo_procesar,
            args=(self.archivo_seleccionado, config),
            daemon=True
        )
        hilo.start()

    def _hilo_procesar(self, ruta_entrada, config):
        try:
            base, ext = os.path.splitext(ruta_entrada)
            ruta_salida = base + "_mejorado" + ext

            pasos_total = sum([
                config["tipo"] == "video" and config["cortar_silencios"],
                config["tipo"] == "video" and config["eliminar_muletillas"],
                config["color_grading"],
                config["tipo"] == "video" and config["audio_fades"],
                config["esrgan"],
            ])
            if pasos_total == 0:
                self._estado("No hay mejoras seleccionadas.", 0)
                return

            paso_actual = 0
            archivo_actual = ruta_entrada
            temps = []

            def tmp(sufijo):
                p = base + f"_tmp_{sufijo}" + ext
                temps.append(p)
                return p

            # ── Video: silencios ──────────────────────
            if config["tipo"] == "video" and config["cortar_silencios"]:
                self._estado("Eliminando silencios...", paso_actual / pasos_total)
                out = tmp("sil")
                sys.path.insert(0, BASE)
                from automontaje.modulos.mejoras import cortar_silencios
                cortar_silencios(archivo_actual, out)
                archivo_actual = out
                paso_actual += 1

            # ── Video: muletillas ─────────────────────
            if config["tipo"] == "video" and config["eliminar_muletillas"]:
                self._estado("Eliminando muletillas...", paso_actual / pasos_total)
                out = tmp("mul")
                from automontaje.modulos.mejoras import eliminar_muletillas
                eliminar_muletillas(archivo_actual, out)
                archivo_actual = out
                paso_actual += 1

            # ── Color grading ─────────────────────────
            if config["color_grading"]:
                self._estado(f"Aplicando color grading '{config['estilo_color']}'...",
                             paso_actual / pasos_total)
                out = tmp("col")
                from automontaje.modulos.mejoras import aplicar_color_grading
                aplicar_color_grading(archivo_actual, out, estilo=config["estilo_color"])
                archivo_actual = out
                paso_actual += 1

            # ── Video: audio fades ────────────────────
            if config["tipo"] == "video" and config["audio_fades"]:
                self._estado("Añadiendo audio fades...", paso_actual / pasos_total)
                out = tmp("fad")
                from automontaje.modulos.mejoras import anadir_audio_fades
                anadir_audio_fades(archivo_actual, out)
                archivo_actual = out
                paso_actual += 1

            # ── Real-ESRGAN ───────────────────────────
            if config["esrgan"]:
                self._estado("Aplicando super resolucion con IA (Real-ESRGAN)...",
                             paso_actual / pasos_total)
                if config["tipo"] == "imagen":
                    out = base + "_mejorado_4K" + ext
                    cmd = [
                        ESRGAN_EXE,
                        "-i", archivo_actual,
                        "-o", out,
                        "-n", config["modelo_esrgan"]
                    ]
                    subprocess.run(cmd, capture_output=True)
                    archivo_actual = out
                else:
                    # Video: extraer frames, mejorar, reensamblar
                    out = base + "_mejorado_4K.mp4"
                    self._procesar_video_esrgan(archivo_actual, out, config["modelo_esrgan"])
                    archivo_actual = out
                ruta_salida = archivo_actual
                paso_actual += 1

            # ── Mover a destino final ─────────────────
            if archivo_actual != ruta_salida and os.path.exists(archivo_actual):
                shutil.copy2(archivo_actual, ruta_salida)

            # Limpiar temporales
            for t in temps:
                if os.path.exists(t) and t != ruta_salida:
                    try:
                        os.remove(t)
                    except Exception:
                        pass

            self._estado(f"Listo! Guardado en: {os.path.basename(ruta_salida)}", 1.0)
            self.after(0, lambda: messagebox.showinfo(
                "Completado",
                f"Archivo mejorado guardado en:\n{ruta_salida}"
            ))
            self._ultima_salida = os.path.dirname(ruta_salida)

        except Exception as e:
            self._estado(f"Error: {e}", 0)
            self.after(0, lambda: messagebox.showerror("Error", str(e)))

        finally:
            self.procesando = False
            self.after(0, lambda: self.btn_procesar.configure(
                state="normal", text="PROCESAR"
            ))

    def _procesar_video_esrgan(self, ruta_entrada, ruta_salida, modelo):
        """Extrae frames, aplica ESRGAN y reensambla."""
        import json as _json
        base_tmp = ruta_entrada.replace(".mp4", "_esrgan_tmp")
        frames_orig  = os.path.join(base_tmp, "orig")
        frames_mejor = os.path.join(base_tmp, "mejor")
        os.makedirs(frames_orig,  exist_ok=True)
        os.makedirs(frames_mejor, exist_ok=True)

        # Obtener FPS
        res = subprocess.run(
            ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_streams", ruta_entrada],
            capture_output=True, text=True
        )
        info = _json.loads(res.stdout)
        fps = 30.0
        for s in info["streams"]:
            if s["codec_type"] == "video":
                n, d = s["r_frame_rate"].split("/")
                fps = float(n) / float(d)
                break

        # Extraer frames
        subprocess.run([
            "ffmpeg", "-y", "-i", ruta_entrada,
            os.path.join(frames_orig, "frame_%08d.png")
        ], capture_output=True)

        # ESRGAN
        subprocess.run([
            ESRGAN_EXE, "-i", frames_orig, "-o", frames_mejor,
            "-n", modelo, "-f", "png"
        ], capture_output=True)

        # Reensamblar
        temp_v = ruta_salida.replace(".mp4", "_v.mp4")
        subprocess.run([
            "ffmpeg", "-y", "-framerate", str(fps),
            "-i", os.path.join(frames_mejor, "frame_%08d.png"),
            "-c:v", "libx264", "-preset", "slow", "-crf", "18",
            "-pix_fmt", "yuv420p", temp_v
        ], capture_output=True)

        subprocess.run([
            "ffmpeg", "-y", "-i", temp_v, "-i", ruta_entrada,
            "-c:v", "copy", "-c:a", "aac", "-b:a", "128k",
            "-shortest", ruta_salida
        ], capture_output=True)

        # Limpiar
        if os.path.exists(temp_v):
            os.remove(temp_v)
        shutil.rmtree(base_tmp, ignore_errors=True)

    def _estado(self, texto, progreso):
        self.after(0, lambda: self.lbl_estado.configure(text=texto))
        self.after(0, lambda: self.barra.set(progreso))

    def _abrir_carpeta_salida(self):
        carpeta = getattr(self, "_ultima_salida", None)
        if not carpeta:
            if self.archivo_seleccionado:
                carpeta = os.path.dirname(self.archivo_seleccionado)
            else:
                carpeta = BASE
        os.startfile(carpeta)


# ─── Arranque ────────────────────────────────────────────

if __name__ == "__main__":
    app = App()
    app.mainloop()
