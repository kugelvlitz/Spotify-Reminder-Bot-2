from telegram import *
from telegram.ext import *
import logging
import random
import datetime
import calendar
from calendar import monthrange
import xlsxwriter
import json
import os
import requests

# -*- coding: utf-8 -*-

# ---------------------------------------------------------------------------------------------


# noinspection PyUnusedLocal
def add_months(sourcedate, months):
    """
        :param sourcedate: Objeto datetime.date.
        :param months: meses a añadir a sourcedate.
        :return: Objeto datetime.date con months agregados.
    """
    month = sourcedate.month - 1 + months
    year = int(sourcedate.year + month / 12)
    month = month % 12 + 1
    day = min(sourcedate.day, calendar.monthrange(year, month)[1])

    return datetime.date(year, month, day)


# noinspection PyUnusedLocal
class Main:
    def __init__(self, token):
        self.token = token
        self.hoy = datetime.date.today()
        self.user = ""
        with open("registro", "r") as f:
            temp = json.load(fp=f)
            self.monto = temp["monto_USD"]
            self.dia_pago = temp["dia_pago"]
            self.reminders = temp["recordatorio"]

        with open("master.json", "r") as f:
            self.master = json.load(fp=f)

        # Updater genera instancia de bot segun token
        self.updater = Updater(token=self.token)

        # Genera instancia de dispatcher
        self.dispatcher = self.updater.dispatcher

        # Genera instancia de Job
        self.job = self.updater.job_queue

        # Logger
        # noinspection SpellCheckingInspection
        logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

    # -------------------------------------------------------------------------------------------

        # Handlers

        start_handler = CommandHandler(command="start", callback=self.start)
        self.dispatcher.add_handler(start_handler)

        aux_handler = MessageHandler(filters=GenericFilter("Más"), callback=self.aux_menu)
        self.dispatcher.add_handler(aux_handler)

        estado_handler = MessageHandler(filters=GenericFilter("Estado 🌗"), callback=self.estado)
        self.dispatcher.add_handler(estado_handler)

        confirmar_handler = ConversationHandler(
            entry_points=[MessageHandler(filters=GenericFilter("Confirmar ⚡️"), callback=self.confirmar)],

            states={
                0: [MessageHandler(filters=Filters.text, callback=self.enviar_confirmar)]
            },

            fallbacks=[MessageHandler(filters=GenericFilter("Regresar"), callback=self.main_menu)]
        )
        self.dispatcher.add_handler(confirmar_handler)

        registro_handler = MessageHandler(filters=GenericFilter("Mi registro 💎"), callback=self.registro)
        self.dispatcher.add_handler(registro_handler)

        atrasos_handler = MessageHandler(filters=GenericFilter("Atrasos ⌛️"), callback=self.atrasos)
        self.dispatcher.add_handler(atrasos_handler)

        set_estado_handler = ConversationHandler(
            entry_points=[MessageHandler(filters=GenericFilter("🌕 Set Estado 🌑"), callback=self.set_estado)],

            states={
                0: [RegexHandler('^(Julio&Carolina Rodriguez|Diana Alvarado|Fabian Montero)$',
                                 callback=self.estado_usuario)],

                1: [RegexHandler('^(T|F)', callback=self.cambiar_estado)],

                2: [RegexHandler('^(Sí|No)', callback=self.cambiar_estado_sin_conversion)]
            },
            fallbacks=[MessageHandler(filters=GenericFilter("Regresar"), callback=self.main_menu)]
        )
        self.dispatcher.add_handler(set_estado_handler)

        set_notification_handler = ConversationHandler(
            entry_points=[MessageHandler(filters=GenericFilter("Notificaciones ⌚️"), callback=self.set_notification)],

            states={
                0: [MessageHandler(filters=Filters.text, callback=self.put_notification)]
            },
            fallbacks=[MessageHandler(filters=GenericFilter("Regresar"), callback=self.main_menu)]
        )
        self.dispatcher.add_handler(set_notification_handler)

        regresar_handler = MessageHandler(filters=GenericFilter("Regresar"), callback=self.main_menu)
        self.dispatcher.add_handler(regresar_handler)

        job_notify_atraso = Job(callback=self.custom_notify, interval=datetime.timedelta(days=1))
        self.job.put(job_notify_atraso, next_t=datetime.timedelta(hours=5))

        fecha_handler = MessageHandler(filters=GenericFilter("Siguiente Fecha 🔭"), callback=self.siguiente_fecha)
        self.dispatcher.add_handler(fecha_handler)

        job_notify_atraso = Job(callback=self.notify_atraso, interval=datetime.timedelta(days=1))
        self.job.put(job_notify_atraso, next_t=datetime.timedelta(hours=5))

        job_notify_monthly = Job(callback=self.monthly_reminder, interval=datetime.timedelta(days=1))
        self.job.put(job_notify_monthly, next_t=datetime.timedelta(hours=5))

        fecha_command_handler = CommandHandler(command="siguiente", callback=self.siguiente_fecha)
        self.dispatcher.add_handler(fecha_command_handler)

        quote_handler = MessageHandler(filters=GenericFilter("Quote 🚬"), callback=self.quote)
        self.dispatcher.add_handler(quote_handler)

        quote_command_handler = CommandHandler(command="quote", callback=self.quote)
        self.dispatcher.add_handler(quote_command_handler)

        set_monto_handler = ConversationHandler(
            entry_points=[MessageHandler(filters=GenericFilter("Cambiar Monto"), callback=self.set_monto)],

            states={
                0: [MessageHandler(filters=Filters.text, callback=self.cambiar_monto)]
            },
            fallbacks=[MessageHandler(filters=GenericFilter("Regresar"), callback=self.main_menu)]
        )
        self.dispatcher.add_handler(set_monto_handler)

        save_handler = MessageHandler(filters=GenericFilter("Save"), callback=self.save)
        self.dispatcher.add_handler(save_handler)

        help_handler = MessageHandler(filters=GenericFilter("Ayuda ❔"), callback=self.help)
        self.dispatcher.add_handler(help_handler)

        help_command_handler = CommandHandler(command="ayuda", callback=self.help)
        self.dispatcher.add_handler(help_command_handler)

        regresar_handler = MessageHandler(filters=GenericFilter("Regresar"), callback=self.main_menu)
        self.dispatcher.add_handler(regresar_handler)

        nonsense_handler = MessageHandler(filters=Filters.text, callback=self.nonsense)
        self.dispatcher.add_handler(nonsense_handler)

        # Pone updater en loop
        self.updater.start_polling()

    # ------------------------------------------------------------------------------------------

    def start(self, bot, update):
        """
            :param bot:
            :param update:
            Al ejecutarse revisa si el usuario está registrado.
            De ser así, muestra los botones con que interactúa el usuario.
            De no ser así, envía un mensaje notificando al usuario no-registrado.
            Dentro del grupo las acciones disponibles son limitadas.

            Avg. Runtime: 0.3 secs
        """
        identidad = update.message.chat_id
        if identidad == self.master["admin"]["id"]:
            reply_keyboard = [["🌕 Set Estado 🌑", "Siguiente Fecha 🔭"], ["Notificaciones ⌚️", "Mi registro 💎"],
                              ["Atrasos ⌛️", "Más"]]

            update.message.reply_text(
                f"Bienvenido {update.message.chat.first_name}\nQue puedo hacer por usted?",
                reply_markup=ReplyKeyboardMarkup(keyboard=reply_keyboard, one_time_keyboard=False)
            )

        elif identidad in self.master["ids"] or identidad == self.master["admin"]["id"]:
            reply_keyboard = [["Estado 🌗", "Siguiente Fecha 🔭"], ['Confirmar ⚡️', "Mi registro 💎"],
                              ["Notificaciones ⌚️", "Más"]]

            update.message.reply_text(
                f"Bienvenido {update.message.chat.first_name}\nQue puedo hacer por usted?",
                reply_markup=ReplyKeyboardMarkup(keyboard=reply_keyboard, one_time_keyboard=False)
            )

        elif update.message.chat_id == self.master["grupo"]["id"]:
            reply_keyboard = [["Siguiente Fecha 🔭", "Quote 🚬"]]

            update.message.reply_text(
                "En que los puedo ayudar?",
                reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=False)
            )

        else:
            admin_handle = self.master["admin"]["handle"]
            reply_keyboard = [["🕋 Solicitar Ingreso 🕋"]]

            update.message.reply_text(
                reply_keyboard=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True),
                text=f"Usted no está registrado como usuario.\nPara más información contactar a {admin_handle}")

    def main_menu(self, bot, update):
        """
            :param bot:
            :param update:
            :return: -1 (si es admin o miembro), termina cualquier conversación.
            Regresa el menú principal.
        """
        identidad = update.message.chat_id
        if identidad == self.master["admin"]["id"]:
            reply_keyboard = [["🌕 Set Estado 🌑", "Siguiente Fecha 🔭"], ["Notificaciones ⌚️", "Mi registro 💎"],
                              ["Atrasos ⌛️", "Más"]]

            update.message.reply_text(
                "Regresando",
                reply_markup=ReplyKeyboardMarkup(keyboard=reply_keyboard, one_time_keyboard=False)
            )
            return -1

        elif identidad in self.master["ids"]:
            reply_keyboard = [["Estado 🌗", "Siguiente Fecha 🔭"], ['Confirmar ⚡️', "Mi registro 💎"],
                              ["Notificaciones ⌚️", "Más"]]

            update.message.reply_text(
                "Regresando",
                reply_markup=ReplyKeyboardMarkup(keyboard=reply_keyboard, one_time_keyboard=False)
            )
            return -1

        elif update.message.chat_id == self.master["grupo"]["id"]:
            reply_keyboard = [["Siguiente Fecha 🔭", "Quote 🚬"]]

            update.message.reply_text(
                "Regresando",
                reply_markup=ReplyKeyboardMarkup(keyboard=reply_keyboard, one_time_keyboard=False)
            )

        else:
            reply_keyboard = [["Ayuda ❔"]]

            update.message.reply_text(
                "Regresando",
                reply_markup=ReplyKeyboardMarkup(keyboard=reply_keyboard, one_time_keyboard=False)
            )

    def aux_menu(self, bot, update):
        """
            :param bot:
            :param update:
            Muestra el menú con más opciones
        """
        identidad = update.message.chat_id
        if identidad == self.master["admin"]["id"]:
            reply_keyboard = [["Save", "Quote 🚬"], ["Añadir Miembro", "Cambiar Monto"], ["Ayuda ❔", "Regresar"]]

            update.message.reply_text(
                "Más opciones",
                reply_markup=ReplyKeyboardMarkup(keyboard=reply_keyboard, one_time_keyboard=False)
            )
        elif identidad in self.master["ids"]:
            reply_keyboard = [["Quote 🚬", "Ayuda ❔"], ["Regresar"]]

            update.message.reply_text(
                "Más opciones",
                reply_markup=ReplyKeyboardMarkup(keyboard=reply_keyboard, one_time_keyboard=False))

        elif identidad == self.master["grupo"]["id"]:
            reply_keyboard = [["Siguiente Fecha 🔭", "Quote 🚬"]]

            update.message.reply_text(
                "Más opciones",
                reply_markup=ReplyKeyboardMarkup(keyboard=reply_keyboard, one_time_keyboard=False))

    def estado(self, bot, update):
        """
            :param bot:
            :param update:
            Le muestra al usuario el estado de su pago mensual.

            Avg. Runtime: 0.3 sec
        """
        current_id = update.message.chat_id

        if current_id == self.master["admin"]["id"]:
            update.message.reply_text(text="Administrador\nEl dinero será rebajado de forma automática.")

        elif current_id in self.master["ids"]:

            i = self.master["ids"].index(current_id)

            if self.master["estados"][i]:
                update.message.reply_text(text="Su pago de este mes fue exitosamente registrado.")

            else:
                update.message.reply_text(text="No se encontró pago correspondiente a este mes.")

        elif current_id == self.master["grupo"]["id"]:
            update.message.reply_text(text="El grupo no posee estado.")

        else:
            handle = self.master["admin"]["handle"]
            update.message.reply_text(
                text=f"Usted no está registrado como usuario.\nPara más información contactar a {handle}")

    def siguiente_fecha(self, bot, update):
        """
            :param bot:
            :param update:
            Indica la siguiente fecha de pago.
        """
        if update.message.chat_id in self.master["ids"]\
                or update.message.chat_id == self.master["admin"]["id"]\
                or update.message.chat_id == self.master["grupo"]["id"]:

            self.hoy = datetime.date.today()

            if datetime.date.today().day <= self.dia_pago:
                self.hoy = datetime.date.today()
                mes = self.hoy.month
                year = self.hoy.year
                diferencia = self.dia_pago-self.hoy.day

                update.message.reply_text(text=
                                          f"La siguiente fecha de pago es el {self.dia_pago}/{mes}/{year}\n"
                                          f"Faltan {diferencia} días")

            else:
                self.hoy = datetime.date.today()
                next_month = add_months(self.hoy, 1)
                days_in_current_month = monthrange(self.hoy.year, self.hoy.month)
                days_to_next_month = ((days_in_current_month[1]-self.hoy.day)+self.dia_pago)

                update.message.reply_text(
                    text=f"La siguiente fecha es el {self.dia_pago}/{next_month.month}/{next_month.year}\n"
                         f"Faltan {days_to_next_month} días")

        else:
            handle = self.master["admin"]["handle"]
            update.message.reply_text(
                text=f"Usted no está registrado como usuario.\nPara más información contactar a {handle}")

    # noinspection PyMethodMayBeStatic
    def quote(self, bot, update):
        """
            :param bot:
            :param update:
            :return: Una random quote de quotes.txt
        """
        with open("quotes.txt", "r") as f:
            replies = f.readlines()
        line = random.randint(0, len(replies) - 1)
        update.message.reply_text(text=replies[line])

    def help(self, bot, update):
        """
            :param bot:
            :param update:
            Responde los comandos disponibles al usuario y lo que cada uno hace.
        """
        if update.message.chat_id == self.master["admin"]["id"]:
            update.message.reply_text(text=
                                      "~Set Estado - Modificar estados y registros de usuarios\n"
                                      "~Siguiente Fecha - La siguiente fecha de pago\n"
                                      "~Mi registro - Envía archivo .xlsx con sus registro de todos sus pagos\n"
                                      "~Notificaciones - Usted puede configurar sus propias notificaciones\n"
                                      "~Atrasos - Muestra atrasos de usuarios\n"
                                      "~Save - Salva master y registro en disco\n"
                                      "~Cambiar monto - Cambia el monto en USD del cobro mensual\n"
                                      "~Añadir miembro - añade miembro a master y registro\n"
                                      "~Quote - quote(puede que sea NSFW)"
                                      )

        elif update.message.chat_id in self.master["ids"]:
            update.message.reply_text(text=
                                      "~Estado - Le indica el estado de su pago actual mensual\n"
                                      "~Siguiente Fecha - La siguiente fecha de pago\n"
                                      "~Confirmar - Envía un pedido para confirmar su pago\n"
                                      "~Mi registro - Envía archivo .xlsx con sus registro de todos sus pagos\n"
                                      "~Notificaciones - Usted puede configurar sus propias notificaciones\n"
                                      "~Quote - quote(puede que sea NSFW)"
                                      )

        elif update.message.chat_id == self.master["grupo"]["id"]:
            update.message.reply_text(text=
                                      "-Funcionalidad limitada en grupo-\n"
                                      "/siguiente - Siguiente fecha de pago\n"
                                      "/quote - quote(puede que sea NSFW)"
                                      )

        else:
            handle = self.master["admin"]["handle"]
            update.message.reply_text(
                text=f"Usted no está registrado como usuario.\nPara más información contactar a {handle}")

    def set_notification(self, bot, update):
        """
            :param bot:
            :param update:
            Le permite al usuario personalizar sus propias notificaciones mensuales a su gusto
            independientemente de las de los demás usuarios.
            :return: 0, indica el siguiente paso en la conversación: put_notificación
        """
        reply_keyboard = [["Quitar mi notificación actual"], ["Regresar"]]
        update.message.reply_text(text="Que día desea recibir la notificación mensual?\n\n"
                                       "Debe estar entre 1 y el día de pago.\n"
                                       f"Es el {self.dia_pago}, en este momento.",
                                  reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True))
        return 0

    def put_notification(self, bot, update):
        """
            :param bot:
            :param update:
            :return: -1, termina la conversación
            Si el usuario quitar la notificación mensual actual lo permite,
            si ingresa una entrada inválida, le responde con el error,
            si ingresa una fecha válida la ingresa a master
        """
        response = update.message.text
        if response == "Quitar mi notificación actual":
            if update.message.chat_id == self.master["admin"]["id"]:
                self.master["admin"]["notify"] = None
                update.message.reply_text(text="Listo, la notificación a sido eliminada.")

            elif update.message.chat_id in self.master["ids"]:
                user = self.master["ids"].index(update.message.chat_id)
                self.master["notify"] = None
                update.message.reply_text(text="Listo, la notificación a sido eliminada.")

        else:
            try:
                response = int(response)
                if 0 < response <= self.dia_pago:
                    if update.message.chat_id == self.master["admin"]["id"]:
                        self.master["admin"]["notify"] = response

                        update.message.reply_text(text="Listo! Notificación configurada.")

                    elif update.message.chat_id in self.master["ids"]:
                        i = self.master["ids"].index(update.message.chat_id)
                        self.master["notify"][i] = response

                        update.message.reply_text(text="Listo! Notificación configurada.")

            except (TypeError, ValueError):
                if response != "Regresar":
                    update.message.reply_text(text="Entrada inválida")

        self.save(bot, update)
        self.main_menu(bot, update)
        return -1

    def custom_notify(self, bot, update):
        """
            :param bot:
            :param update:
            Diariamente revisa si hoy debe dar una notificación personalizada a algún o algunos usuarios,
            en caso de haber, las da.
        """
        self.hoy = datetime.date.today()
        if self.hoy.day == self.master["admin"]["notify"]:
            bot.send_message(chat_id=self.master["admin"]["id"],
                             text=f"Hola {self.master['admin']['nombre']}\n"
                                  "Esta es su notificación personalizada,"
                                  "que le recuerda que la siguiente fecha de pago es el:\n\n"
                                  f"{self.hoy}\n"
                                  f"Faltan {self.dia_pago-self.hoy} días")

        elif self.hoy.day in self.master["notify"]:
            queue = {
                "usuarios": [],
                "nombres": []
            }
            for i in range(0, len(self.master["notify"])):
                if self.master["notify"][i] == self.hoy.day:
                    queue["usuarios"] += self.master["ids"][i]
                    queue["nombres"] += self.master["nombres"][i]

            for i in range(0, len(queue["usuarios"])):
                bot.send_message(chat_id=queue["usuarios"][i],
                                 text=f"Hola {queue['nombres'][i]}\n"
                                      "Esta es su notificación personalizada,"
                                      "que le recuerda que la siguiente fecha de pago es el:\n\n"
                                      f"{self.hoy}\n"
                                      f"Faltan {self.dia_pago-self.hoy} días")

    def notify_atraso(self, bot, update):
        """
            :param bot:
            :param update:
            Le notifica al usuario los días que tiene de atraso al pago mensual.
            En caso de haber, maneja la cantidad de dias desde el atraso.
        """
        if datetime.date.today().day > self.dia_pago:
            dias = datetime.date.today().day
            for i in range(0, len(self.master["estado"])):
                if not self.master["estado"][i]:
                    if dias-self.dia_pago == 1:
                        dialogo_usuario = "Usted está atrasado(a) 1 día del pago."
                        dialogo_admin = f"{self.master['nombres'][i]} AKA {self.master['handles'][i]}" \
                                        "\n\nEstá atrasado 1 día"
                    else:
                        dialogo_usuario = f"Usted está atrasado(a) {dias-self.dia_pago} días."
                        dialogo_admin = f"{self.master['nombres'][i]} AKA {self.master['handles'][i]}" \
                                        f"\n\nEstá atrasado {dias-self.dia_pago} días"

                    bot.send_message(chat_id=self.master["ids"][i], text=dialogo_usuario)
                    bot.send_message(chat_id=self.master["admin"]["id"], text=dialogo_admin)

    def atrasos(self, bot, update):
        """
            :param bot:
            :param update:
            Solo para admin.
            Le permite al admin identificar los usuarios con atrasos y los días rezagados del mismo.
        """
        if update.message.chat_id == self.master["admin"]["id"] and datetime.date.today().day > self.dia_pago:
            hay_atraso = False
            dias = datetime.date.today().day
            for i in range(len(self.master["estados"])):
                if not self.master["estados"][i]:
                    hay_atraso = True
                    handle = self.master["handles"][i]
                    update.message.reply_text(text=
                                              f"{handle}\nEstá atrasado.")

            if hay_atraso:
                update.message.reply_text(text=
                                          f"Días de atraso : {dias-self.dia_pago}")

            else:
                update.message.reply_text(text=
                                          "No hay atrasos.")

        else:
            update.message.reply_text(text="No hay atrasos")

    def monthly_reminder(self, bot, update):
        """
            :param bot:
            :param update:
            Solo para grupo.
            Le notifica al grupo n veces por mes, cuantos días faltan para la siguiente fecha de pago.
        """
        self.hoy = datetime.date.today()
        if self.hoy.day in self.reminders:
            eta = self.dia_pago-self.hoy.day
            bot.send_message(chat_id=self.master["grupo"]["id"],
                             text=f"Recuerden que la fecha limite de pago es en:\n {eta} días.")

    def confirmar(self, bot, update):
        """
            :param bot:
            :param update:
            :return: 0, siguiente paso en la conversación.
            Le permite al usuario confirmar que ha realizando el pago.

            Avg. Runtime: 0.29 sec
        """
        if update.message.chat_id in self.master["ids"]:
            reply_keyboard = [["Sí", "No"], ["Regresar"]]
            update.message.reply_text(text="Está seguro?",
                                      reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True))

        return 0

    def enviar_confirmar(self, bot, update):
        """
            :param bot:
            :param update:
            :return: -1, termina la conversación
            Si decide confirmar, se enviará la notificación al admin,
            si decide no confirmar, no no envía notificación,
            si ingresa una entrada inválida, le envía el error y termina la conversación.
        """
        response = update.message.text
        nombre = update.message.chat.first_name
        if response == "Sí":
            handle = update.message.chat.username
            bot.send_message(chat_id=self.master["admin"]["id"],
                             text=f"{nombre}\n(@{handle})\n\nQuiere confirmar")

            update.message.reply_text(text="Confirmación enviada, respuesta pendiente.")

        elif response == "No":
            update.message.reply_text(text="Ok")

        else:
            update.message.reply_text(text="Entrada invalida")

        self.main_menu(bot, update)
        return -1

    def registro(self, bot, update):
        """
            :param bot:
            :param update:
            Le envía un archivo .xlsx con su registro de pago al usuario correspondiente.
        """
        if update.message.chat_id == self.master["admin"]["id"] or update.message.chat_id in self.master["ids"]:
            user = update.message.chat_id

            with open('registro', 'r') as f:
                log = json.load(fp=f)

            workbook = xlsxwriter.Workbook("Registro.xlsx")
            worksheet = workbook.add_worksheet()

            row = 0
            column = 0
            worksheet.write(row, column, update.message.chat.first_name)
            row += 1
            worksheet.write(row, column, "Fechas")
            for i in log[f"{user}"]["pagos_fecha"]:
                row += 1
                worksheet.write(row, column, i)

            row = 1
            column += 1
            total = 0
            worksheet.write(1, column, "Pagos UDS")
            for i in log[f"{user}"]["pagos_USD"]:
                row += 1
                total += i
                worksheet.write(row, column, f"{i}$")
            column += 1
            worksheet.write(1, column, "Total USD")
            worksheet.write(2, column, f"{total}$")

            row = 1
            column += 1
            total = 0
            worksheet.write(1, column, "Pagos CRC")
            for i in log[f"{user}"]["pagos_CRC"]:
                row += 1
                total += i
                worksheet.write(row, column, f"{i}c")
            column += 1
            worksheet.write(1, column, "Total CRC")
            worksheet.write(2, column, f"{total}c")

            workbook.close()

            update.message.reply_text(text=f"{update.message.chat.first_name} este es un registro de todos sus pagos:")
            bot.send_document(chat_id=update.message.chat_id, document=open("Registro.xlsx", "rb"))

            os.remove("Registro.xlsx")

    def set_estado(self, bot, update):
        """
            :param bot:
            :param update:
            :return: 0, siguiente paso en la conversación.
            Solo para admin.
            Permite al admin definir el estado de pago de un usuario determinado mediante una conversación.
        """
        if update.message.chat_id == self.master["admin"]["id"]:
            reply_keyboard = [self.master["nombres"], ["Regresar"]]
            update.message.reply_text(text="Cual usuario?",
                                      reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True))

            return 0

    def estado_usuario(self, bot, update):
        """
            :param bot:
            :param update:
            :return: 1, siguiente paso en la conversación.
            Solo para admin.
            Pregunta a que valor desea actualizar el estado del usuario
        """
        self.user = update.message.text

        reply_keyboard = [["T", "F"], ["Regresar"]]

        update.message.reply_text(text="Cual es el nuevo estado?",
                                  reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True))

        return 1

    def cambiar_estado(self, bot, update):
        """
            :param bot:
            :param update:
            En caso de fallar conexión de request
            :return: 2, siguiente paso en la conexión
            Solo para admin.
            Toma el valor del estado y lo ingresa a master con la información debida.
        """
        response = update.message.text
        i = self.master["nombres"].index(self.user)
        user = str(self.master["ids"][i])

        if response == "T":
            try:
                self.master["estados"][i] = True

                exchange = requests.get(
                    "")

                exchange_rate = exchange.json()["quotes"]["USDCRC"]

                with open('registro', 'r') as f:
                    log = json.load(fp=f)

                log[user]["pagos_fecha"] += [str(datetime.date.today())]
                log[user]["pagos_USD"] += [self.monto]
                log[user]["pagos_CRC"] += [self.monto*exchange_rate]

                with open('registro', 'w') as f:
                    json.dump(log, fp=f, indent=True)

                self.save(bot, update)

                update.message.reply_text(text="Estado actualizado")

                self.main_menu(bot, update)
            except requests.ConnectionError:
                reply_keyboard = [["Sí", "No"]]
                update.message.reply_text(text="Error en conexión a API.\nSeguir de todos modos?",
                                          reply_keyboard=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True))

                return 2
            except FileNotFoundError:
                update.message.reply_text(text="Error\nArchivo no encontrado")
                self.main_menu(bot, update)

        elif response == "F":
            self.master["estados"][i] = False

            self.save(bot, update)

            update.message.reply_text(text="Estado actualizado a Falso")

        self.user = ""

        self.main_menu(bot, update)

    def cambiar_estado_sin_conversion(self, bot, update):
        """
            :param bot:
            :param update:
            :return: -1, termina la conversación.
            Solo para admin.
            En caso de fallar la conexión en request del anterior paso y que el admin decida igual continuar,
            toma el valor del estado y lo ingresa con la información debida con excepción del la conversión de
            USD A CRC.
        """
        response = update.message.reply_text
        i = self.master["nombres"].index(self.user)
        user = str(self.master["ids"][i])

        if response == "Sí":
            try:
                with open('registro', 'r') as f:
                    log = json.load(fp=f)

                log[user]["pagos_fecha"] += [str(datetime.date.today())]
                log[user]["pagos_USD"] += [self.monto]
                log[user]["pagos_CRC"] += [None]

                with open('registro', 'w') as f:
                    json.dump(log, fp=f, indent=True)

                self.save(bot, update)

                update.message.reply_text(text="Estado actualizado")

                self.main_menu(bot, update)

            except FileNotFoundError:
                update.message.reply_text(text="Error\nArchivo no encontrado")
                self.main_menu(bot, update)

        else:
            update.message.reply_text(text="Ok")
            self.main_menu(bot, update)

        return - 1

    # noinspection PyMethodMayBeStatic
    def set_monto(self, bot, update):
        """
            :param bot:
            :param update:
            :return: 0, siguiente estado en la conversación.
            Pregunta por un valor para cambiar en monto mensual de pago.
        """
        update.message.reply_text(text="¿A cuando lo desea cambiar? -$-")

        return 0

    def cambiar_monto(self, bot, update):
        """
        :param bot:
        :param update:
        :return: -1, termina la conversación.
        Toma el valor dado e intentar cambiar el monto de pago por este,
        en caso de la entrada ser inválida, envía el error y termina la conversación.
        """
        if update.message.text == "Regresar":
            return -1
        try:
            nuevo_monto = float(update.message.text)
            self.monto = nuevo_monto
            update.message.reply_text(f"El nuevo monto es {self.monto}")
            self.save(bot, update)

        except:
            update.message.reply_text("Entrada inválida")

        self.aux_menu(bot, update)
        return -1

    def save(self, bot, update):
        """
            :param bot:
            :param update:
            Guarda la información de self.master, self.monto y self.dia_pago en la base de datos.
            También guarda la última información en un backup.
        """
        try:
            with open("master.json", "w") as f:
                json.dump(self.master, fp=f, indent=True)

            with open("registro", "r") as f:
                temp = json.load(fp=f)
            temp["monto_USD"] = self.monto
            temp["dia_pago"] = self.dia_pago
            with open("registro", "w") as f:
                json.dump(temp, fp=f,  indent=True)

            with open("backup.txt", "w") as f:
                json.dump(self.master, fp=f)

        except FileNotFoundError:
            user = update.message.chat_id
            if user in self.master["ids"]:
                i = self.master["ids"].index(user)
                nombre = self.master["nombres"][i]

            elif user == self.master["admin"]["id"]:
                nombre = self.master["admin"]["nombre"]

            bot.send_message(chat_id=self.master["admin"]["id"], text=f"Fallo al guardar acción de {nombre}")

    # noinspection PyMethodMayBeStatic
    def nonsense(self, bot, update):
        """
            :param bot:
            :param update:
            Envía mensaje indicando que no se encontró un mensaje o comando válido.
        """
        update.message.reply_text(text="Comando inválido ♿️")


class GenericFilter(BaseFilter):
    """
        Hereda de BaseFilter para formar un custom filter.

        En este caso toma un mensaje como parámetro e indica
        si ese mensaje se encuentra en el texto enviado por el usuario.
    """
    def __init__(self, command):
        self.command = command

    def filter(self, message):
        return self.command in message.text

