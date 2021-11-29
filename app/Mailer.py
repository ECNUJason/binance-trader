import smtplib
from email import encoders
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart


class Mailer:

    def __init__(self):
        pass
    
    def send_email(self, message, logger, subject = "Trader Business"):
        #sender是邮件发送人邮箱，passWord是服务器授权码，mail_host是服务器地址（这里是QQsmtp服务器）
        sender = 'fake@qq.com'#
        passWord = 'fake'
        mail_host = 'smtp.qq.com'
        #receivers是邮件接收人，用列表保存，可以添加多个
        receivers = ['fake@qq.com','fake@126.com']

        #设置email信息
        msg = MIMEMultipart()
        #邮件主题
        msg['Subject'] = subject
        #发送方信息
        msg['From'] = sender
        #邮件正文是MIMEText:
        msg_content = message
        msg.attach(MIMEText(msg_content, 'plain', 'utf-8'))
        # # 添加附件就是加上一个MIMEBase，从本地读取一个图片:
        # with open(u'/Users/xxx/1.jpg', 'rb') as f:
        #     # 设置附件的MIME和文件名，这里是jpg类型,可以换png或其他类型:
        #     mime = MIMEBase('image', 'jpg', filename='Lyon.png')
        #     # 加上必要的头信息:
        #     mime.add_header('Content-Disposition', 'attachment', filename='Lyon.png')
        #     mime.add_header('Content-ID', '<0>')
        #     mime.add_header('X-Attachment-Id', '0')
        #     # 把附件的内容读进来:
        #     mime.set_payload(f.read())
        #     # 用Base64编码:
        #     encoders.encode_base64(mime)
        #     # 添加到MIMEMultipart:
        #     msg.attach(mime)

        #登录并发送邮件
        try:
            #QQsmtp服务器的端口号为465或587
            s = smtplib.SMTP_SSL("smtp.qq.com", 465)
            # s.set_debuglevel(1)
            s.login(sender,passWord)
            #给receivers列表中的联系人逐个发送邮件
            for item in receivers:
                try:
                    msg['To'] = to = item
                    s.sendmail(sender,to,msg.as_string())
                    logger.info('Success to send to:{}'.format(item))
                    break
                except Exception as e:
                    logger.warning("Falied to send to:{}, error:{}".format(item, e))
            s.quit()
        except smtplib.SMTPException as e:
            logger.error("Falied, %s",e)

if __name__ == "__main__":
    mailer = Mailer()
    mailer.send_email("hello world!")