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
        self.geometry("1180x820")
        self.minsize(920, 720)
        self.resizable(True, True)

        self.archivo_seleccionado = None
        self.procesando = False
        self.nivel_voz_actual = "media"

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

        self.contenido = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.contenido.pack(fill="both", expand=True, padx=18, pady=(0, 10))

        # ── Zona de archivo ──────────────────────────────
        self.frame_archivo = ctk.CTkFrame(self.contenido, height=130, corner_radius=12)
        self.frame_archivo.pack(fill="x", padx=12, pady=(0, 16))
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
        frame_opciones = ctk.CTkFrame(self.contenido, corner_radius=12)
        frame_opciones.pack(fill="x", padx=12, pady=(0, 16))

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
        self.var_color      = ctk.BooleanVar(value=False)
        self.var_fades      = ctk.BooleanVar(value=True)
        self.var_muletillas = ctk.BooleanVar(value=False)
        self.var_vertical   = ctk.BooleanVar(value=False)
        self.var_subtitulos = ctk.BooleanVar(value=False)
        self.var_limpiar_voz = ctk.BooleanVar(value=False)

        ctk.CTkCheckBox(col_izq, text="Eliminar silencios automaticamente",
                        variable=self.var_silencios).pack(anchor="w", pady=3)
        ctk.CTkCheckBox(col_izq, text="Color grading extra (opcional)",
                        variable=self.var_color).pack(anchor="w", pady=3)
        ctk.CTkCheckBox(col_izq, text="Fades de audio (30ms)",
                        variable=self.var_fades).pack(anchor="w", pady=3)
        ctk.CTkCheckBox(col_izq, text="Eliminar muletillas (umm, eh...)",
                        variable=self.var_muletillas).pack(anchor="w", pady=3)
        ctk.CTkCheckBox(col_izq, text="Convertir a vertical 9:16",
                        variable=self.var_vertical).pack(anchor="w", pady=3)
        ctk.CTkCheckBox(col_izq, text="Subtitulos automaticos (Whisper)",
                        variable=self.var_subtitulos).pack(anchor="w", pady=3)
        ctk.CTkCheckBox(col_izq, text="Aislar voz / quitar musica de fondo (IA)",
                        variable=self.var_limpiar_voz).pack(anchor="w", pady=3)

        # Estilo de color
        frame_estilo = ctk.CTkFrame(col_izq, fg_color="transparent")
        frame_estilo.pack(anchor="w", pady=(8, 0))
        ctk.CTkLabel(frame_estilo, text="Estilo color:").pack(side="left", padx=(0, 8))
        self.estilo_color = ctk.CTkOptionMenu(
            frame_estilo,
            values=["natural_claro", "neutro", "calido", "cinematico"],
            width=130
        )
        self.estilo_color.set("natural_claro")
        self.estilo_color.pack(side="left")

        # Columna derecha — Mejoras de imagen
        col_der = ctk.CTkFrame(frame_opciones, fg_color="transparent")
        col_der.grid(row=1, column=2, columnspan=2, padx=20, pady=(0, 12), sticky="nw")

        # ── Mejora real (FFmpeg) ──────────────────────
        ctk.CTkLabel(col_der, text="Mejora real (FFmpeg) — para fotos/videos reales",
                     font=ctk.CTkFont(size=13, weight="bold"),
                     text_color="#4ade80").pack(anchor="w", pady=(0, 4))

        self.var_mejora_real = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(col_der,
                        text="Nitidez + brillo + color vivo + resolucion x2\n(rapido, natural, sin plastificar)",
                        variable=self.var_mejora_real).pack(anchor="w", pady=3)

        frame_nivel = ctk.CTkFrame(col_der, fg_color="transparent")
        frame_nivel.pack(anchor="w", pady=(4, 0))
        ctk.CTkLabel(frame_nivel, text="Nivel:").pack(side="left", padx=(0, 8))
        self.nivel_mejora = ctk.CTkOptionMenu(
            frame_nivel,
            values=["suave", "media", "fuerte"],
            width=110
        )
        self.nivel_mejora.set("media")
        self.nivel_mejora.pack(side="left")

        ctk.CTkLabel(col_der,
                     text="suave  = toque ligero\nmedia  = equilibrado (recomendado)\nfuerte = maxima mejora",
                     font=ctk.CTkFont(size=11), text_color="gray",
                     justify="left").pack(anchor="w", pady=(4, 10))

        # ── Super resolución IA (ESRGAN) ──────────────
        ctk.CTkLabel(col_der, text="Super resolucion IA (Real-ESRGAN) — para ampliar",
                     font=ctk.CTkFont(size=13, weight="bold"),
                     text_color="#4EA8DE").pack(anchor="w", pady=(4, 4))

        self.var_esrgan = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(col_der, text="Ampliar x4 con IA (lento)\nBueno para imagenes pequenas o dibujos",
                        variable=self.var_esrgan,
                        onvalue=True, offvalue=False).pack(anchor="w", pady=3)

        frame_modelo = ctk.CTkFrame(col_der, fg_color="transparent")
        frame_modelo.pack(anchor="w", pady=(6, 0))
        ctk.CTkLabel(frame_modelo, text="Modelo:").pack(side="left", padx=(0, 8))
        self.modelo_esrgan = ctk.CTkOptionMenu(
            frame_modelo,
            values=["realesrgan-x4plus", "realesrgan-x4plus-anime"],
            width=200
        )
        self.modelo_esrgan.pack(side="left")

        # ── Editor por comandos ─────────────────────────
        frame_comandos = ctk.CTkFrame(self.contenido, corner_radius=12)
        frame_comandos.pack(fill="x", padx=12, pady=(0, 16))

        ctk.CTkLabel(
            frame_comandos, text="Editor por comandos",
            font=ctk.CTkFont(size=15, weight="bold")
        ).pack(anchor="w", padx=20, pady=(12, 4))

        self.txt_comando = ctk.CTkTextbox(frame_comandos, height=70, width=700)
        self.txt_comando.pack(fill="x", padx=20, pady=(0, 8))
        self.txt_comando.insert(
            "1.0",
            "Ejemplo: hazlo vertical para reels, mejora calidad media, más claro y quita silencios"
        )

        frame_cmd_botones = ctk.CTkFrame(frame_comandos, fg_color="transparent")
        frame_cmd_botones.pack(fill="x", padx=20, pady=(0, 12))
        ctk.CTkButton(
            frame_cmd_botones,
            text="Aplicar comando",
            command=self._aplicar_comando,
            width=180, height=34
        ).pack(side="left", padx=(0, 8))
        ctk.CTkButton(
            frame_cmd_botones,
            text="Contrato desde comando",
            command=self._contrato_desde_comando,
            width=210, height=34,
            fg_color="#555", hover_color="#444"
        ).pack(side="left")
        self.lbl_plan_comando = ctk.CTkLabel(
            frame_cmd_botones,
            text="",
            font=ctk.CTkFont(size=12),
            text_color="gray",
            anchor="w",
            justify="left",
            wraplength=760
        )
        self.lbl_plan_comando.pack(side="left", padx=(12, 0))

        frame_contrato = ctk.CTkFrame(self.contenido, corner_radius=12)
        frame_contrato.pack(fill="x", padx=12, pady=(0, 16))

        ctk.CTkLabel(
            frame_contrato, text="Contrato de herramientas",
            font=ctk.CTkFont(size=15, weight="bold")
        ).pack(anchor="w", padx=20, pady=(12, 4))

        self.txt_contrato = ctk.CTkTextbox(frame_contrato, height=145, width=700)
        self.txt_contrato.pack(fill="x", padx=20, pady=(0, 8))
        self.txt_contrato.insert("1.0", json.dumps({
            "herramientas": [
                {"herramienta": "mejora_real", "parametros": {"nivel": "media"}},
                {"herramienta": "vertical_9_16", "parametros": {}}
            ]
        }, indent=2, ensure_ascii=False))

        frame_contrato_botones = ctk.CTkFrame(frame_contrato, fg_color="transparent")
        frame_contrato_botones.pack(fill="x", padx=20, pady=(0, 12))
        ctk.CTkButton(
            frame_contrato_botones,
            text="Validar contrato",
            command=self._validar_contrato,
            width=170, height=34,
            fg_color="#555", hover_color="#444"
        ).pack(side="left", padx=(0, 8))
        self.btn_ejecutar_contrato = ctk.CTkButton(
            frame_contrato_botones,
            text="Ejecutar contrato",
            command=self._ejecutar_contrato,
            width=180, height=34,
            fg_color="#1f6aa5", hover_color="#1a5a8f"
        )
        self.btn_ejecutar_contrato.pack(side="left")
        self.lbl_contrato = ctk.CTkLabel(
            frame_contrato_botones,
            text="",
            font=ctk.CTkFont(size=12),
            text_color="gray",
            anchor="w",
            justify="left",
            wraplength=720
        )
        self.lbl_contrato.pack(side="left", padx=(12, 0))

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

        # ── Botones inferiores ───────────────────────────
        self.btn_procesar = ctk.CTkButton(
            self,
            text="PROCESAR",
            command=self._procesar,
            width=400, height=50,
            font=ctk.CTkFont(size=16, weight="bold"),
            fg_color="#1f6aa5", hover_color="#1a5a8f"
        )
        self.btn_procesar.pack(pady=(0, 10), padx=30)

        frame_botones2 = ctk.CTkFrame(self, fg_color="transparent")
        frame_botones2.pack(pady=(0, 10))

        ctk.CTkButton(
            frame_botones2,
            text="Reiniciar",
            command=self._reiniciar,
            width=160, height=38,
            font=ctk.CTkFont(size=13),
            fg_color="#555", hover_color="#444"
        ).pack(side="left", padx=(0, 8))

        self.btn_ver = ctk.CTkButton(
            frame_botones2,
            text="Ver archivo procesado",
            command=self._ver_archivo,
            width=200, height=38,
            font=ctk.CTkFont(size=13),
            fg_color="#2d6a4f", hover_color="#1b4332",
            state="disabled"
        )
        self.btn_ver.pack(side="left", padx=(0, 8))

        ctk.CTkButton(
            frame_botones2,
            text="Abrir carpeta",
            command=self._abrir_carpeta_salida,
            width=150, height=38,
            fg_color="transparent", border_width=1,
            font=ctk.CTkFont(size=13)
        ).pack(side="left")

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
            "formato_vertical":   self.var_vertical.get(),
            "subtitulos":         self.var_subtitulos.get(),
            "limpiar_voz":        self.var_limpiar_voz.get(),
            "nivel_voz":          getattr(self, "nivel_voz_actual", "media"),
            "mejora_real":        self.var_mejora_real.get(),
            "nivel_mejora":       self.nivel_mejora.get(),
            "esrgan":             self.var_esrgan.get(),
            "modelo_esrgan":      self.modelo_esrgan.get(),
        }

        # Aviso: ampliar video con IA tarda horas
        if config["tipo"] == "video" and config["esrgan"]:
            seguir = messagebox.askyesno(
                "Aviso - proceso muy largo",
                "Has marcado 'Ampliar x4 con IA' para un VIDEO.\n\n"
                "Esto procesa cada fotograma con IA y puede tardar\n"
                "VARIAS HORAS (2-6 h) segun la duracion del video.\n\n"
                "Recomendado para video: usa solo 'Mejora real'\n"
                "(rapido, ~1 minuto, sin IA).\n\n"
                "¿Quieres continuar igualmente con la IA x4?"
            )
            if not seguir:
                return

        self.procesando = True
        self.btn_procesar.configure(state="disabled", text="Procesando...")
        self.barra.set(0)

        hilo = threading.Thread(
            target=self._hilo_procesar,
            args=(self.archivo_seleccionado, config),
            daemon=True
        )
        hilo.start()

    def _aplicar_comando(self):
        comando = self.txt_comando.get("1.0", "end").strip()
        try:
            sys.path.insert(0, BASE)
            from automontaje.modulos.editor_comandos import parsear_comando_edicion
            plan = parsear_comando_edicion(comando)
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo interpretar el comando:\n{e}")
            return

        cfg = plan["config"]
        self.var_silencios.set(cfg["cortar_silencios"])
        self.var_muletillas.set(cfg["eliminar_muletillas"])
        self.var_color.set(cfg["color_grading"])
        self.estilo_color.set(cfg["estilo_color"])
        self.var_fades.set(cfg["audio_fades"])
        self.var_mejora_real.set(cfg["mejora_real"])
        self.nivel_mejora.set(cfg["nivel_mejora"])
        self.var_vertical.set(cfg["formato_vertical"])
        self.var_subtitulos.set(cfg.get("subtitulos", False))
        self.var_limpiar_voz.set(cfg.get("limpiar_voz", False))
        self.nivel_voz_actual = cfg.get("nivel_voz", "media")
        self.var_esrgan.set(cfg["esrgan"])
        self.modelo_esrgan.set(cfg["modelo_esrgan"])

        acciones = ", ".join(plan["acciones"])
        avisos = " | ".join(plan["avisos"])
        texto = acciones if not avisos else f"{acciones} | {avisos}"
        self.lbl_plan_comando.configure(text=texto[:110])

    def _contrato_desde_comando(self):
        comando = self.txt_comando.get("1.0", "end").strip()
        try:
            sys.path.insert(0, BASE)
            from automontaje.modulos.editor_comandos import parsear_comando_contrato
            plan = parsear_comando_contrato(comando)
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo generar el contrato:\n{e}")
            return

        if not plan["contrato"]["herramientas"]:
            detalle = "\n".join(plan["avisos"]) or "No se detectaron acciones por tiempo."
            messagebox.showwarning("Sin contrato", detalle)
            self.lbl_plan_comando.configure(text=detalle[:110])
            return

        self.txt_contrato.delete("1.0", "end")
        self.txt_contrato.insert(
            "1.0",
            json.dumps(plan["contrato"], indent=2, ensure_ascii=False)
        )
        acciones = ", ".join(plan["acciones"])
        avisos = " | ".join(plan["avisos"])
        texto = acciones if not avisos else f"{acciones} | {avisos}"
        self.lbl_plan_comando.configure(text=texto[:110])
        self._validar_contrato()

    def _leer_contrato_ui(self):
        texto = self.txt_contrato.get("1.0", "end").strip()
        if not texto:
            raise ValueError("El contrato esta vacio.")
        try:
            return json.loads(texto)
        except json.JSONDecodeError as e:
            raise ValueError(f"JSON invalido: linea {e.lineno}, columna {e.colno}: {e.msg}")

    def _validar_contrato(self):
        try:
            contrato = self._leer_contrato_ui()
            sys.path.insert(0, BASE)
            from automontaje.modulos.contrato_edicion import validar_contrato_herramientas
            validacion = validar_contrato_herramientas(contrato)
        except Exception as e:
            self.lbl_contrato.configure(text=f"Error: {e}", text_color="#ff8a80")
            messagebox.showerror("Contrato invalido", str(e))
            return

        if not validacion["valido"]:
            detalle = "\n".join(validacion["errores"][:8])
            self.lbl_contrato.configure(text="Contrato invalido", text_color="#ff8a80")
            messagebox.showerror("Contrato invalido", detalle)
            return

        pasos = len(validacion["contrato"]["herramientas"])
        avisos = " | ".join(validacion["avisos"])
        texto = f"Contrato valido: {pasos} herramienta(s)"
        if avisos:
            texto += f" | {avisos}"
        self.lbl_contrato.configure(text=texto[:140], text_color="#4ade80")

    def _ejecutar_contrato(self):
        if self.procesando:
            return
        if not self.archivo_seleccionado:
            messagebox.showwarning("Aviso", "Primero selecciona un video.")
            return

        ext = os.path.splitext(self.archivo_seleccionado)[1].lower()
        if ext not in EXTENSIONES_VIDEO:
            messagebox.showwarning("Aviso", "Los contratos de herramientas se aplican a videos.")
            return

        try:
            contrato = self._leer_contrato_ui()
            sys.path.insert(0, BASE)
            from automontaje.modulos.contrato_edicion import validar_contrato_herramientas
            validacion = validar_contrato_herramientas(contrato)
        except Exception as e:
            messagebox.showerror("Contrato invalido", str(e))
            return

        if not validacion["valido"]:
            messagebox.showerror("Contrato invalido", "\n".join(validacion["errores"][:8]))
            return

        self.procesando = True
        self.btn_procesar.configure(state="disabled")
        self.btn_ejecutar_contrato.configure(state="disabled", text="Ejecutando...")
        self.barra.set(0.08)
        hilo = threading.Thread(
            target=self._hilo_contrato,
            args=(self.archivo_seleccionado, contrato),
            daemon=True
        )
        hilo.start()

    def _hilo_contrato(self, ruta_entrada, contrato):
        try:
            base, ext = os.path.splitext(ruta_entrada)
            ruta_salida = self._ruta_salida_unica(base + "_contrato" + ext)
            self._estado("Ejecutando contrato de herramientas...", 0.15)

            sys.path.insert(0, BASE)
            from automontaje.modulos.contrato_edicion import ejecutar_contrato_herramientas
            resultado = ejecutar_contrato_herramientas(ruta_entrada, ruta_salida, contrato)
            if not resultado["exito"]:
                raise RuntimeError("\n".join(resultado.get("errores", ["Error desconocido"])))

            self._ultimo_archivo = ruta_salida
            self._ultima_salida = os.path.dirname(ruta_salida)
            pasos = ", ".join(resultado.get("pasos_ejecutados", []))
            self._estado(f"Contrato listo! Guardado en: {os.path.basename(ruta_salida)}", 1.0)
            self.after(0, lambda: self.btn_ver.configure(state="normal"))
            self.after(0, lambda: self.lbl_contrato.configure(
                text=(f"Ejecutado: {pasos}" if pasos else "Contrato ejecutado"),
                text_color="#4ade80"
            ))
            self.after(0, lambda: messagebox.showinfo(
                "Contrato completado",
                f"Video generado:\n{ruta_salida}"
            ))
        except Exception as e:
            self._estado(f"Error contrato: {e}", 0)
            self.after(0, lambda: self.lbl_contrato.configure(
                text=f"Error: {str(e)[:120]}",
                text_color="#ff8a80"
            ))
            self.after(0, lambda: messagebox.showerror("Error contrato", str(e)))
        finally:
            self.procesando = False
            self.after(0, lambda: self.btn_procesar.configure(state="normal"))
            self.after(0, lambda: self.btn_ejecutar_contrato.configure(
                state="normal", text="Ejecutar contrato"
            ))

    def _hilo_procesar(self, ruta_entrada, config):
        try:
            base, ext = os.path.splitext(ruta_entrada)
            ruta_salida = self._ruta_salida_unica(base + "_mejorado" + ext)

            pasos_total = sum([
                config["tipo"] == "video" and config["cortar_silencios"],
                config["tipo"] == "video" and config["eliminar_muletillas"],
                config["color_grading"],
                config["tipo"] == "video" and config["audio_fades"],
                config["mejora_real"],
                config["tipo"] == "video" and config["formato_vertical"],
                config["tipo"] == "video" and config.get("limpiar_voz", False),
                config["tipo"] == "video" and config.get("subtitulos", False),
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

            # ── Mejora real (FFmpeg) ──────────────────
            if config["mejora_real"]:
                self._estado("Aplicando mejora real (brillo + nitidez + color + x2)...",
                             paso_actual / pasos_total)
                out = tmp("real")
                from automontaje.modulos.mejoras import mejorar_imagen_real
                mejorar_imagen_real(archivo_actual, out, nivel=config["nivel_mejora"])
                archivo_actual = out
                paso_actual += 1

            # ── Formato vertical 9:16 ──────────────────
            if config["tipo"] == "video" and config["formato_vertical"]:
                self._estado("Convirtiendo a formato vertical 9:16...",
                             paso_actual / pasos_total)
                out = tmp("vertical")
                from automontaje.modulos.mejoras import convertir_vertical_9_16
                convertir_vertical_9_16(archivo_actual, out)
                archivo_actual = out
                paso_actual += 1

            # ── Limpiar voz / quitar ruido ─────────────
            if config["tipo"] == "video" and config.get("limpiar_voz", False):
                self._estado("Aislando voz y quitando musica/fondo con IA...",
                             paso_actual / pasos_total)
                out = tmp("voz")
                from automontaje.modulos.mejoras import limpiar_voz
                limpiar_voz(archivo_actual, out, nivel=config.get("nivel_voz", "media"))
                archivo_actual = out
                paso_actual += 1

            # ── Subtitulos automaticos (Whisper) ───────
            if config["tipo"] == "video" and config.get("subtitulos", False):
                self._estado("Generando subtitulos con Whisper (transcribiendo)...",
                             paso_actual / pasos_total)
                out = tmp("subs")
                from automontaje.modulos.mejoras import anadir_subtitulos_automaticos
                anadir_subtitulos_automaticos(archivo_actual, out)
                archivo_actual = out
                paso_actual += 1

            # ── Real-ESRGAN ───────────────────────────
            if config["esrgan"]:
                self._estado("Aplicando super resolucion con IA (Real-ESRGAN)...",
                             paso_actual / pasos_total)

                # Verificar que el ejecutable y el modelo existen
                if not os.path.exists(ESRGAN_EXE):
                    raise RuntimeError(
                        f"No se encontro Real-ESRGAN en:\n{ESRGAN_EXE}"
                    )
                modelo = config["modelo_esrgan"]
                modelo_param = os.path.join(ESRGAN_DIR, "models", modelo + ".param")
                modelo_bin   = os.path.join(ESRGAN_DIR, "models", modelo + ".bin")
                if not (os.path.exists(modelo_param) and os.path.exists(modelo_bin)):
                    raise RuntimeError(
                        f"El modelo '{modelo}' no existe en la carpeta models.\n"
                        "Modelos disponibles: realesrgan-x4plus, realesrgan-x4plus-anime"
                    )

                if config["tipo"] == "imagen":
                    out = self._ruta_salida_unica(base + "_mejorado_4K" + ext)
                    r = subprocess.run([
                        ESRGAN_EXE,
                        "-i", archivo_actual,
                        "-o", out,
                        "-n", modelo
                    ], capture_output=True, text=True,
                       encoding="utf-8", errors="ignore")
                    if r.returncode != 0 or not os.path.exists(out):
                        detalle = (r.stderr or r.stdout or "").strip()[-700:]
                        raise RuntimeError(f"Real-ESRGAN fallo:\n{detalle}")
                    archivo_actual = out
                else:
                    # Video: extraer frames, mejorar, reensamblar
                    out = self._ruta_salida_unica(base + "_mejorado_4K.mp4")
                    self._procesar_video_esrgan(archivo_actual, out, modelo)
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

            if not os.path.exists(ruta_salida):
                raise RuntimeError(
                    f"El archivo de salida no se genero:\n{ruta_salida}\n\n"
                    "Alguna mejora fallo durante el proceso."
                )

            self._ultimo_archivo = ruta_salida
            self._ultima_salida  = os.path.dirname(ruta_salida)
            self._estado(f"Listo! Guardado en: {os.path.basename(ruta_salida)}", 1.0)
            self.after(0, lambda: self.btn_ver.configure(state="normal"))
            self.after(0, lambda: messagebox.showinfo(
                "Completado",
                f"Archivo mejorado guardado en:\n{ruta_salida}\n\nHaz clic en 'Ver archivo procesado' para abrirlo."
            ))

        except Exception as e:
            self._estado(f"Error: {e}", 0)
            self.after(0, lambda: messagebox.showerror("Error", str(e)))

        finally:
            self.procesando = False
            self.after(0, lambda: self.btn_procesar.configure(
                state="normal", text="PROCESAR"
            ))

    def _ruta_salida_unica(self, ruta_base):
        """Evita sobrescribir resultados anteriores y reduce confusion de versiones."""
        if not os.path.exists(ruta_base):
            return ruta_base
        base, ext = os.path.splitext(ruta_base)
        for i in range(1, 1000):
            candidata = f"{base}_{i:03d}{ext}"
            if not os.path.exists(candidata):
                return candidata
        raise RuntimeError("No se pudo crear un nombre de salida disponible.")

    def _procesar_video_esrgan(self, ruta_entrada, ruta_salida, modelo):
        """Extrae frames, aplica ESRGAN y reensambla. Lanza error si algo falla."""
        import json as _json

        def _run(cmd, desc):
            r = subprocess.run(cmd, capture_output=True, text=True,
                               encoding="utf-8", errors="ignore")
            if r.returncode != 0:
                detalle = (r.stderr or r.stdout or "").strip()[-700:]
                raise RuntimeError(f"{desc} fallo:\n{detalle}")
            return r

        base_tmp = ruta_entrada.replace(".mp4", "_esrgan_tmp")
        frames_orig  = os.path.join(base_tmp, "orig")
        frames_mejor = os.path.join(base_tmp, "mejor")
        os.makedirs(frames_orig,  exist_ok=True)
        os.makedirs(frames_mejor, exist_ok=True)

        try:
            # Obtener FPS
            res = subprocess.run(
                ["ffprobe", "-v", "quiet", "-print_format", "json",
                 "-show_streams", ruta_entrada],
                capture_output=True, text=True, encoding="utf-8", errors="ignore"
            )
            info = _json.loads(res.stdout)
            fps = 30.0
            for s in info["streams"]:
                if s["codec_type"] == "video":
                    n, d = s["r_frame_rate"].split("/")
                    fps = float(n) / float(d)
                    break

            # Extraer frames
            self._estado("Real-ESRGAN: extrayendo fotogramas del video...")
            _run([
                "ffmpeg", "-y", "-i", ruta_entrada,
                os.path.join(frames_orig, "frame_%08d.png")
            ], "Extraccion de fotogramas")

            n_frames = len([f for f in os.listdir(frames_orig)
                            if f.lower().endswith(".png")])
            if n_frames == 0:
                raise RuntimeError("No se extrajo ningun fotograma del video.")

            # ESRGAN por lotes (cada lote = proceso nuevo => evita que
            # un microcorte de GPU corrompa el resto en negro)
            def _brillo(img):
                """Devuelve el brillo medio (YAVG 0-255) de una imagen."""
                r = subprocess.run(
                    ["ffmpeg", "-i", img, "-vf",
                     "signalstats,metadata=print:key=lavfi.signalstats.YAVG",
                     "-f", "null", "-"],
                    capture_output=True, text=True,
                    encoding="utf-8", errors="ignore"
                )
                for tok in (r.stderr or "").split():
                    if tok.startswith("lavfi.signalstats.YAVG="):
                        try:
                            return float(tok.split("=")[1])
                        except ValueError:
                            pass
                return None

            lista = sorted(f for f in os.listdir(frames_orig)
                           if f.lower().endswith(".png"))
            total = len(lista)
            LOTE = 50
            batch_in = os.path.join(base_tmp, "_lote")
            hecho = 0

            for ini in range(0, total, LOTE):
                lote = lista[ini:ini + LOTE]
                self._estado(
                    f"Real-ESRGAN: mejorando con IA... "
                    f"{min(ini + LOTE, total)}/{total} fotogramas "
                    f"(esto tarda, no cierres la ventana)"
                )

                # Verificar lote: hasta 2 intentos
                ok = False
                for intento in range(2):
                    if os.path.exists(batch_in):
                        shutil.rmtree(batch_in, ignore_errors=True)
                    os.makedirs(batch_in, exist_ok=True)
                    for fn in lote:
                        shutil.copy2(os.path.join(frames_orig, fn),
                                     os.path.join(batch_in, fn))

                    _run([
                        ESRGAN_EXE, "-i", batch_in, "-o", frames_mejor,
                        "-n", modelo, "-f", "png"
                    ], f"Real-ESRGAN (fotogramas {ini + 1}-{min(ini + LOTE, total)})")

                    # Comprobar que el lote no salio en negro
                    salida0 = os.path.join(frames_mejor, lote[0])
                    b_out = _brillo(salida0)
                    b_in  = _brillo(os.path.join(frames_orig, lote[0]))
                    if (b_out is None or b_out >= 20 or
                            (b_in is not None and b_in < 20)):
                        ok = True
                        break  # lote correcto

                if not ok:
                    raise RuntimeError(
                        "Real-ESRGAN devolvio fotogramas en negro (microcorte "
                        "de la GPU).\n\nSoluciones:\n"
                        "  - Cierra otros programas que usen la tarjeta grafica "
                        "(juegos, navegador con video, etc.)\n"
                        "  - Prueba con un video mas corto\n"
                        "  - Vuelve a intentarlo"
                    )
                hecho += len(lote)

            shutil.rmtree(batch_in, ignore_errors=True)

            n_mejor = len([f for f in os.listdir(frames_mejor)
                           if f.lower().endswith(".png")])
            if n_mejor == 0:
                raise RuntimeError("Real-ESRGAN no genero ningun fotograma mejorado.")

            # Reensamblar video (sin audio)
            self._estado(f"Real-ESRGAN: reensamblando video ({n_mejor} fotogramas)...")
            temp_v = ruta_salida.replace(".mp4", "_v.mp4")
            _run([
                "ffmpeg", "-y", "-framerate", str(fps),
                "-i", os.path.join(frames_mejor, "frame_%08d.png"),
                "-c:v", "libx264", "-preset", "slow", "-crf", "18",
                "-pix_fmt", "yuv420p", "-profile:v", "high", "-level", "4.0",
                temp_v
            ], "Reensamblado de video")

            # Añadir audio original
            self._estado("Real-ESRGAN: uniendo audio original...")
            _run([
                "ffmpeg", "-y", "-i", temp_v, "-i", ruta_entrada,
                "-map", "0:v:0", "-map", "1:a:0?",
                "-c:v", "copy", "-c:a", "aac", "-b:a", "128k", "-ar", "44100",
                "-movflags", "+faststart", "-shortest", ruta_salida
            ], "Union de audio")

            if os.path.exists(temp_v):
                os.remove(temp_v)

            if not os.path.exists(ruta_salida):
                raise RuntimeError("El video final no se genero correctamente.")

        finally:
            shutil.rmtree(base_tmp, ignore_errors=True)

    def _estado(self, texto, progreso=None):
        self.after(0, lambda: self.lbl_estado.configure(text=texto))
        if progreso is not None:
            self.after(0, lambda: self.barra.set(progreso))

    def _ver_archivo(self):
        """Abre el archivo procesado con el programa predeterminado."""
        archivo = getattr(self, "_ultimo_archivo", None)
        if archivo and os.path.exists(archivo):
            os.startfile(archivo)
        else:
            messagebox.showinfo("Aviso", "No hay archivo procesado todavia.")

    def _reiniciar(self):
        """Resetea la interfaz al estado inicial."""
        self.archivo_seleccionado = None
        self.procesando = False
        self.lbl_archivo.configure(
            text="Ningun archivo seleccionado\nHaz clic en 'Seleccionar archivo' para empezar",
            text_color="gray"
        )
        self.lbl_estado.configure(text="Listo para procesar")
        self.barra.set(0)
        self.btn_procesar.configure(state="normal", text="PROCESAR")
        self.var_silencios.set(True)
        self.var_color.set(False)
        self.var_fades.set(True)
        self.var_muletillas.set(False)
        self.var_vertical.set(False)
        self.var_subtitulos.set(False)
        self.var_limpiar_voz.set(False)
        self.nivel_voz_actual = "media"
        self.var_mejora_real.set(True)
        self.var_esrgan.set(False)
        self.nivel_mejora.set("media")
        self.estilo_color.set("natural_claro")
        self.modelo_esrgan.set("realesrgan-x4plus")
        self.btn_ver.configure(state="disabled")
        self.lbl_plan_comando.configure(text="")
        self.lbl_contrato.configure(text="", text_color="gray")
        self._ultimo_archivo = None

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
