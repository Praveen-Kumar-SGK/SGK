# from django.db import models
from djongo import models
from django.utils import timezone
# import django
import datetime
import pytz
IST = pytz.timezone('Asia/Kolkata')

# Create your models here.
class msd_dataset(models.Model):
    category = models.CharField(max_length=50,null=False)
    text = models.TextField(null=False)
    language_code = models.CharField(max_length=20,blank=True)
    language = models.CharField(max_length=20,blank=True)
    type = models.CharField(max_length=50,blank=True)

class msd_content(models.Model):
    text = models.TextField(null=False)
    category_actual = models.CharField(max_length=50,null=False)
    category = models.CharField(max_length=50,null=False)
    language_code = models.CharField(max_length=20,blank=True)
    language = models.CharField(max_length=20,blank=True)
    type = models.CharField(max_length=50, blank=True)

class ferrero_header(models.Model):
    text = models.TextField(null=False)
    category = models.CharField(max_length=50,null=False)

class general_dataset(models.Model):
    text = models.TextField(null=False)
    category = models.CharField(max_length=50,null=False)
    brand = models.CharField(max_length=50,null=True)
    domain = models.CharField(max_length=50,null=True)

class undetected_msd_log(models.Model):
    file_name = models.TextField(default='')
    text = models.TextField(null=False)
    header_category = models.CharField(max_length=50,null=False)
    content_category = models.CharField(max_length=50,null=False)
    language_code = models.CharField(max_length=20,blank =True,default='')
    category = models.CharField(max_length=50,default='')
    language = models.CharField(max_length=20,blank=True,default='')

class log_book(models.Model):
    date = models.DateTimeField(default=datetime.datetime.now(IST))
    # date = models.DateTimeField(default=django.utils.timezone.now)
    accounts = models.CharField(null=False,max_length=100)
    input_file = models.CharField(null=False,max_length=100)
    input_body = models.JSONField(null=False)
    output = models.JSONField(null=False)

    class Meta:
        verbose_name = 'Log'
        verbose_name_plural = 'Logs'
        ordering = ['date']

class google_api(models.Model):
    date = models.DateTimeField(default=timezone.localtime())
    data = models.JSONField(null=False)

    class Meta:
        verbose_name = 'Google_api_log'
        verbose_name_plural = 'Google_api_logs'
        ordering = ['date']

class gs1_elements(models.Model):
    gs1_element = models.CharField(null=False,max_length=50)
    enable = models.BooleanField(default=1)

    class Meta:
        verbose_name = 'gs1_element'
        verbose_name_plural = 'gs1_elements'

class logger(models.Model):
    # date = models.DateTimeField(default=datetime.datetime.now(IST))
    date = models.DateTimeField(default=timezone.now)
    account_type = models.CharField(null=False,max_length=100) # CEP | TORNADO
    input_body = models.JSONField(null=False)
    output = models.TextField(null=False)
    error = models.TextField(null=False,default="NO ERROR")

    class Meta:
        verbose_name = 'Logger'
        verbose_name_plural = 'Logger'
        ordering = ['date']
