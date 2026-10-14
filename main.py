"""
PRISMA — Versão Flet (APK de verdade)
Chat + Memória SQLite + Groq
"""

import flet as ft
import sqlite3
import os
import json
from datetime import datetime
from groq import Groq

# =====================
# CONFIGURAÇÃO
# =====================
GROQ_API_KEY = "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"
MODELO = "openai/gpt-oss-20b"
DB_PATH = "prisma.db"

# =====================
# BANCO DE DADOS (SQLite)
# =====================
def iniciar_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS memoria (
            chave TEXT PRIMARY KEY,
            valor TEXT,
            atualizado_em TEXT
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS historico (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            remetente TEXT,
            mensagem TEXT,
            data TEXT
        )
    """)
    conn.commit()
    conn.close()

def salvar_memoria(chave, valor):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        INSERT INTO memoria (chave, valor, atualizado_em)
        VALUES (?, ?, ?)
        ON CONFLICT(chave) DO UPDATE SET valor=excluded.valor, atualizado_em=excluded.atualizado_em
    """, (chave, valor, datetime.now().isoformat()))
    conn.commit()
    conn.close()

def ler_memoria(chave):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT valor FROM memoria WHERE chave = ?", (chave,))
    resultado = c.fetchone()
    conn.close()
    return resultado[0] if resultado else None

def salvar_historico(remetente, mensagem):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT INTO historico (remetente, mensagem, data) VALUES (?, ?, ?)",
              (remetente, mensagem, datetime.now().isoformat()))
    conn.commit()
    conn.close()

def ler_historico(limite=10):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT remetente, mensagem FROM historico ORDER BY id DESC LIMIT ?", (limite,))
    resultado = c.fetchall()
    conn.close()
    return list(reversed(resultado))

# =====================
# PRISMA — CÉREBRO
# =====================
class Prisma:
    def __init__(self):
        self.cliente = Groq(api_key=GROQ_API_KEY)
        iniciar_db()

    def _prompt_sistema(self):
        nome = ler_memoria("nome") or "amigo"
        gostos = ler_memoria("gostos") or ""
        base = (
            f"Você é Prisma, um assistente amigável criado pelo Kauã. "
            f"Responda em português do Brasil, de forma curta (máx 3 frases). "
            f"O usuário se chama {nome}. "
        )
        if gostos:
            base += f"Ele gosta de: {gostos}. "
        base += "NUNCA escreva seu raciocínio interno, apenas a resposta final."
        return base

    def perguntar(self, mensagem):
        try:
            historico = ler_historico(6)
            mensagens = [{"role": "system", "content": self._prompt_sistema()}]
            for rem, msg in historico:
                role = "user" if rem == "usuario" else "assistant"
                mensagens.append({"role": role, "content": msg})
            mensagens.append({"role": "user", "content": mensagem})

            resposta = self.cliente.chat.completions.create(
                model=MODELO,
                messages=mensagens,
                temperature=0.7,
                max_tokens=400,
            )
            texto = resposta.choices[0].message.content.strip()

            salvar_historico("usuario", mensagem)
            salvar_historico("prisma", texto)

            self._auto_aprender(mensagem)
            return texto
        except Exception as e:
            return f"❌ Erro: {str(e)[:100]}"

    def _auto_aprender(self, texto):
        t = texto.lower()
        if "meu nome é" in t:
            nome = t.split("meu nome é", 1)[1].strip().title()
            salvar_memoria("nome", nome)
        elif "eu gosto de" in t:
            gosto = t.split("eu gosto de", 1)[1].strip()
            gostos_atuais = ler_memoria("gostos") or ""
            novos = f"{gostos_atuais}, {gosto}" if gostos_atuais else gosto
            salvar_memoria("gostos", novos)

# =====================
# INTERFACE FLET
# =====================
def main(page: ft.Page):
    page.title = "Prisma"
    page.bgcolor = "#0a0a0a"
    page.theme_mode = ft.ThemeMode.DARK
    page.padding = 0

    prisma = Prisma()

    chat = ft.ListView(expand=True, spacing=10, auto_scroll=True, padding=15)

    def bolha(texto, eh_usuario):
        return ft.Container(
            content=ft.Text(texto, color="white", size=14),
            bgcolor="#008B8B" if eh_usuario else "#1a1a1a",
            padding=12,
            border_radius=12,
            alignment=ft.Alignment.CENTER_RIGHT if eh_usuario else ft.Alignment.CENTER_LEFT,
            width=280,
        )

    def enviar(e):
        texto = campo.value.strip()
        if not texto:
            return
        chat.controls.append(bolha(texto, True))
        campo.value = ""
        page.update()

        digitando = ft.Container(
            content=ft.Text("...", color="#888", italic=True),
            padding=12, border_radius=12, bgcolor="#1a1a1a",
        )
        chat.controls.append(digitando)
        page.update()

        resposta = prisma.perguntar(texto)
        chat.controls.remove(digitando)
        chat.controls.append(bolha(resposta, False))
        page.update()

    campo = ft.TextField(
        hint_text="Digite sua mensagem...",
        on_submit=enviar,
        expand=True,
        bgcolor="#1a1a1a",
        color="white",
        border_color="#00CED1",
        border_radius=25,
    )

    btn_enviar = ft.IconButton(
        icon=ft.Icons.SEND,
        icon_color="#00CED1",
        on_click=enviar,
    )

    header = ft.Container(
        content=ft.Row([
            ft.Text("🔺", size=30),
            ft.Column([
                ft.Text("Prisma", size=20, weight=ft.FontWeight.BOLD, color="white"),
                ft.Text("Todas as cores da acessibilidade", size=10, color="#aaa"),
            ], spacing=0),
        ]),
        bgcolor="#00CED1",
        padding=15,
    )

    for rem, msg in ler_historico(10):
        chat.controls.append(bolha(msg, rem == "usuario"))

    if not chat.controls:
        chat.controls.append(bolha("Olá! Sou o Prisma. Como posso ajudar? 🐾", False))

    page.add(
        header,
        ft.Container(chat, expand=True),
        ft.Container(
            content=ft.Row([campo, btn_enviar]),
            bgcolor="#0f0f0f",
            padding=10,
        ),
    )

ft.run(main)