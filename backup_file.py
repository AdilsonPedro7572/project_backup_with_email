import os
import datetime
import schedule
import time
from netmiko import ConnectHandler, SSHDetect
import tabulate
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from segredos import senha

def fazer_backup_ips_arquivo(file_path, username, password, backup_path):
    backups = []

    with open(file_path, 'r') as file:
        ips = file.readlines()

    for ip in ips:
        device_ip = ip.strip()
        device = {
            'device_type': 'autodetect',
            'ip': device_ip,
            'username': username,
            'password': password
        }

        try:
            # Detectando o tipo de dispositivo
            guesser = SSHDetect(**device)
            device_type = guesser.autodetect()

            if device_type is None:
                print(f"Tipo de dispositivo não detectado para {device_ip}. Pular para o próximo dispositivo.")
                continue

            device['device_type'] = device_type

            # Conectando ao dispositivo
            net_connect = ConnectHandler(**device)

           # Obtendo o hostname dependendo do tipo de dispositivo
            if device['device_type'] == 'cisco_ios':
                hostname_output = net_connect.send_command('show run | i hostname').strip()
                hostname = hostname_output.split()[1] if len(hostname_output.split()) > 1 else ""
            elif device['device_type'] == 'vyos':
                hostname_output = net_connect.send_command('show system hostname').strip()
                hostname = hostname_output.split(':')[1].strip() if ':' in hostname_output else hostname_output
            elif device['device_type'] == 'juniper_junos':
                hostname_output = net_connect.send_command('show configuration system host-name').strip()
                hostname = hostname_output.split(' ')[-1].strip() if len(hostname_output.split(' ')) > 1 else hostname_output
            else:
                raise ValueError(f"Tipo de dispositivo não suportado: {device['device_type']}")

            current_date = datetime.datetime.now().strftime("%Y-%m-%d")

            filename = f"{hostname}_{current_date}_{device_ip}.txt"

            # Executando o comando de backup
            output = net_connect.send_command('show run')

            # Salvando o arquivo de backup no caminho especificado
            filepath = os.path.join(backup_path, filename)
            with open(filepath, 'w') as backup_file:
                backup_file.write(output)

            backups.append([device_ip, hostname, device_type, filepath])
            print(hostname)
            print(f"Backup do dispositivo {device_ip} ({device_type}) concluído. Arquivo salvo em {filepath}")

        except Exception as e:
            print(f"Erro ao fazer backup do dispositivo {device_ip}: {str(e)}")

        finally:
            net_connect.disconnect()

    return backups

def agendar_backup(file_path, username, password, backup_path):
    # Agendando a função para ser executada diariamente às 23:00
    schedule.every().day.at("23:00").do(fazer_backup_ips_arquivo, file_path, username, password, backup_path)

    # Loop para executar as tarefas agendadas
    while True:
        schedule.run_pending()
        time.sleep(1)

        if schedule.jobs == []:
            break

def enviar_email(tabela):
    # Configurar detalhes do e-mail
    remetente = 'adilsoncrente7572@gmail.com'
    destinatario = 'adilsonpedro999@hotmail.com'
    assunto = 'Backup Diário'
    corpo_email = 'Segue em anexo a tabela com os dispositivos que foram feitos backup.'

    # Configurar servidor SMTP
    smtp_server = 'smtp.gmail.com'
    smtp_port = 587
    smtp_username = 'adilsoncrente7572@gmail.com'
    smtp_password = senha

    # Criar mensagem de e-mail
    mensagem = MIMEMultipart()
    mensagem['From'] = remetente
    mensagem['To'] = destinatario
    mensagem['Subject'] = assunto
    mensagem.attach(MIMEText(corpo_email, 'plain'))

    # Converter tabela para texto
    tabela_texto = tabulate.tabulate(tabela, headers=["Endereço IP", "Hostname", "Tipo de Dispositivo", "Caminho do Arquivo"])

    # Anexar tabela ao e-mail
    anexo = MIMEText(tabela_texto, 'plain')
    anexo.add_header('Content-Disposition', 'attachment', filename='backup_table.txt')
    mensagem.attach(anexo)

    # Enviar e-mail
    with smtplib.SMTP(smtp_server, smtp_port) as servidor:
        servidor.starttls()
        servidor.login(smtp_username, smtp_password)
        servidor.send_message(mensagem)

    print("E-mail enviado com sucesso!")

# Exemplo de uso
file_path = 'C:\\Users\\adilson.pedro\\Desktop\\Projects\\gitvscode\\arquivo_ip.txt'  # Caminho do arquivo contendo os endereços IP
username = 'adilson.pedro'
password = 'salvador7572'
backup_path = 'C:/backups'

backups = fazer_backup_ips_arquivo(file_path, username, password, backup_path)

# Exibindo a tabela com os dispositivos que foram feitos backup
headers = ["Endereço IP", "Hostname", "Tipo de Dispositivo", "Caminho do Arquivo"]
print(tabulate.tabulate(backups, headers=headers))

# Enviar e-mail com a tabela de backups
enviar_email(backups)
