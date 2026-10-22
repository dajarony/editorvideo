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
import customtkinter as ctk
from tkinter import filedialog, messagebox

# ─── Config ─────────────────────────────────────────────
BASE        = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)

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
        self.control_actual = None
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
        frame_encuadre = ctk.CTkFrame(col_izq, fg_color="transparent")
        frame_encuadre.pack(anchor="w", padx=(28, 0), pady=(0, 3))
        ctk.CTkLabel(frame_encuadre, text="Encuadre:").pack(side="left", padx=(0, 8))
        self.encuadre_vertical = ctk.CTkOptionMenu(
            frame_encuadre,
            values=["centro", "izquierda", "derecha", "completo"],
            width=120
        )
        self.encuadre_vertical.set("centro")
        self.encuadre_vertical.pack(side="left")
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
        ctk.CTkButton(
            frame_cmd_botones, text="Proponer con modelo local",
            command=self._interpretar_con_modelo, width=205,
            fg_color="#555", hover_color="#444",
        ).pack(side="left", padx=(8, 0))
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

        frame_revision = ctk.CTkFrame(self, fg_color="transparent")
        frame_revision.pack(pady=(0, 10))
        ctk.CTkLabel(frame_revision, text="Previsualizar desde el segundo:").pack(side="left")
        self.segundo_preview = ctk.CTkEntry(frame_revision, width=70)
        self.segundo_preview.insert(0, "0")
        self.segundo_preview.pack(side="left", padx=6)
        self.btn_preview = ctk.CTkButton(frame_revision, text="Comparar antes/después (8 s)",
                                         command=self._previsualizar)
        self.btn_preview.pack(side="left", padx=5)
        self.btn_cancelar = ctk.CTkButton(frame_revision, text="Cancelar", command=self._cancelar,
                                          state="disabled", fg_color="#8b3333")
        self.btn_cancelar.pack(side="left", padx=5)

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

    def _config_actual(self):
        ext = os.path.splitext(self.archivo_seleccionado)[1].lower()
        tipo = "video" if ext in EXTENSIONES_VIDEO else "imagen"
        return {
            "tipo": tipo, "cortar_silencios": self.var_silencios.get(),
            "color_grading": self.var_color.get(), "estilo_color": self.estilo_color.get(),
            "audio_fades": self.var_fades.get(), "eliminar_muletillas": self.var_muletillas.get(),
            "formato_vertical": self.var_vertical.get(), "encuadre_vertical": self.encuadre_vertical.get(),
            "subtitulos": self.var_subtitulos.get(), "limpiar_voz": self.var_limpiar_voz.get(),
            "nivel_voz": self.nivel_voz_actual, "mejora_real": self.var_mejora_real.get(),
            "nivel_mejora": self.nivel_mejora.get(), "esrgan": self.var_esrgan.get(),
            "modelo_esrgan": self.modelo_esrgan.get(),
        }

    def _iniciar_trabajo(self):
        from automontaje.modulos.proceso import ControlProceso
        self.control_actual = ControlProceso(al_progresar=self._estado)
        self.procesando = True
        self.btn_procesar.configure(state="disabled")
        self.btn_preview.configure(state="disabled")
        self.btn_cancelar.configure(state="normal")
        self.barra.set(0)

    def _terminar_trabajo(self):
        self.procesando = False
        self.control_actual = None
        self.after(0, lambda: self.btn_procesar.configure(state="normal", text="PROCESAR"))
        self.after(0, lambda: self.btn_preview.configure(state="normal"))
        self.after(0, lambda: self.btn_cancelar.configure(state="disabled"))

    def _cancelar(self):
        if self.control_actual:
            self.control_actual.cancelar()
            self._estado("Cancelando el trabajo…")

    def _previsualizar(self):
        if self.procesando:
            return
        if not self.archivo_seleccionado:
            messagebox.showwarning("Aviso", "Primero selecciona un vídeo.")
            return
        try:
            desde = float(self.segundo_preview.get())
            if desde < 0:
                raise ValueError()
        except ValueError:
            messagebox.showerror("Segundo inválido", "Escribe un segundo igual o mayor que cero.")
            return
        self._iniciar_trabajo()
        threading.Thread(target=self._hilo_preview, args=(self.archivo_seleccionado,
                        self._config_actual(), desde, self.control_actual), daemon=True).start()

    def _hilo_preview(self, ruta, config, desde, control):
        try:
            from automontaje.modulos.servicio_edicion import previsualizar
            base, _ = os.path.splitext(ruta)
            salida = self._ruta_salida_unica(base + "_comparacion.mp4")
            resultado = previsualizar(ruta, salida, config, desde, control=control)
            if resultado.get("cancelado"):
                self._estado("Previsualización cancelada", 0)
            elif not resultado["exito"]:
                raise RuntimeError("\n".join(resultado.get("errores", [])))
            else:
                self._ultimo_archivo = salida
                self._ultima_salida = os.path.dirname(salida)
                self._estado("Comparación lista: original a la izquierda, editado a la derecha", 1)
                self.after(0, lambda: os.startfile(salida))
        except Exception as exc:
            mensaje = str(exc)
            self._estado("Error de previsualización: " + mensaje, 0)
            self.after(0, lambda mensaje=mensaje: messagebox.showerror("Previsualización", mensaje))
        finally:
            self._terminar_trabajo()

    def _procesar(self):
        if self.procesando:
            return
        if not self.archivo_seleccionado:
            messagebox.showwarning("Aviso", "Primero selecciona un archivo.")
            return

        config = self._config_actual()

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

        self._iniciar_trabajo()
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
        self.encuadre_vertical.set(cfg.get("encuadre_vertical", "centro"))
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

    def _interpretar_con_modelo(self):
        """La propuesta queda visible en el JSON; el botón Ejecutar sigue siendo separado."""
        orden = self.txt_comando.get("1.0", "end").strip()
        self.lbl_plan_comando.configure(text="Consultando el modelo local…")
        def trabajo():
            try:
                from automontaje.modulos.modelo_ordenes import interpretar_orden
                contrato = interpretar_orden(orden)
                def mostrar():
                    self.txt_contrato.delete("1.0", "end")
                    self.txt_contrato.insert("1.0", json.dumps(contrato, ensure_ascii=False, indent=2))
                    self.lbl_plan_comando.configure(text="Revisa el contrato propuesto y pulsa Ejecutar si estás conforme.")
                    self._validar_contrato()
                self.after(0, mostrar)
            except Exception as exc:
                mensaje = str(exc)
                self.after(0, lambda mensaje=mensaje: messagebox.showerror("Modelo local", mensaje))
                self.after(0, lambda: self.lbl_plan_comando.configure(text="La propuesta no se aplicó."))
        threading.Thread(target=trabajo, daemon=True).start()

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
            from automontaje.modulos.contrato_edicion import validar_contrato_herramientas
            validacion = validar_contrato_herramientas(contrato)
        except Exception as e:
            messagebox.showerror("Contrato invalido", str(e))
            return

        if not validacion["valido"]:
            messagebox.showerror("Contrato invalido", "\n".join(validacion["errores"][:8]))
            return

        self._iniciar_trabajo()
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

            from automontaje.modulos.contrato_edicion import ejecutar_contrato_herramientas
            resultado = ejecutar_contrato_herramientas(ruta_entrada, ruta_salida, contrato,
                al_progresar=self._estado, control=self.control_actual)
            if resultado.get("cancelado"):
                self._estado("Edición cancelada", 0)
                return
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
            mensaje = str(e)
            self._estado(f"Error contrato: {e}", 0)
            self.after(0, lambda mensaje=mensaje: self.lbl_contrato.configure(
                text=f"Error: {mensaje[:120]}",
                text_color="#ff8a80"
            ))
            self.after(0, lambda mensaje=mensaje: messagebox.showerror("Error contrato", mensaje))
        finally:
            self._terminar_trabajo()
            self.after(0, lambda: self.btn_ejecutar_contrato.configure(
                state="normal", text="Ejecutar contrato"
            ))

    def _hilo_procesar(self, ruta_entrada, config):
        """Aplica las opciones marcadas con el motor unico (servicio_edicion -> contrato)."""
        try:
            from automontaje.modulos.servicio_edicion import contrato_desde_config, procesar

            if not contrato_desde_config(config)["herramientas"]:
                self._estado("No hay mejoras seleccionadas.", 0)
                return
            base, ext = os.path.splitext(ruta_entrada)
            ruta_salida = self._ruta_salida_unica(base + "_mejorado" + ext)
            resultado = procesar(
                ruta_entrada, ruta_salida, config,
                al_progresar=lambda fraccion, texto: self._estado(texto, fraccion),
                control=self.control_actual,
            )
            if resultado.get("cancelado"):
                self._estado("Edición cancelada", 0)
                return
            if not resultado["exito"]:
                raise RuntimeError("\n".join(resultado.get("errores", ["Error desconocido"])))

            self._ultimo_archivo = ruta_salida
            self._ultima_salida  = os.path.dirname(ruta_salida)
            self._estado(f"Listo! Guardado en: {os.path.basename(ruta_salida)}", 1.0)
            self.after(0, lambda: self.btn_ver.configure(state="normal"))
            self.after(0, lambda: messagebox.showinfo(
                "Completado",
                f"Archivo mejorado guardado en:\n{ruta_salida}\n\nHaz clic en 'Ver archivo procesado' para abrirlo."
            ))

        except Exception as e:
            mensaje = str(e)
            self._estado(f"Error: {e}", 0)
            self.after(0, lambda mensaje=mensaje: messagebox.showerror("Error", mensaje))

        finally:
            self._terminar_trabajo()

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
        if self.procesando:
            self._cancelar()
            return
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
        self.encuadre_vertical.set("centro")
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
