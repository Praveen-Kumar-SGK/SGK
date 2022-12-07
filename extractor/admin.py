from django.contrib import admin
from .models import *
from django import forms
from django.forms import TextInput, Textarea

# Register your models here.

admin.site.site_title = "SGK API INTERFACE"
admin.site.site_header = "SGK API ADMIN"

admin.site.register(google_api)

class view_msd_dataset(admin.ModelAdmin):
    list_display = ('text','category','language_code')
    # list_display = ('text','category','language_code','language','type')
    list_per_page = 30
    # search_fields = ['category',]
    list_filter = ('language_code','category',)

    def text(self, object):
        return object.text

    def category(self, object):
        return object.category

    def language_code(self, object):
        return object.language_code

    # def language(self, object):
    #     return object.language
    #
    # def type(self, object):
    #     return object.type

admin.site.register(msd_dataset,view_msd_dataset)

class view_msd_dataset_contents(admin.ModelAdmin):
    list_display = ('text','category','language_code')
    # list_display = ('text','category','language_code','language','type')
    list_per_page = 30
    # search_fields = ['category',]
    list_filter = ('language_code','category',)

    def text(self, object):
        return object.text

    def category(self, object):
        return object.category

    def language_code(self, object):
        return object.language_code

    # def language(self, object):
    #     return object.language
    #
    # def type(self, object):
    #     return object.type

admin.site.register(msd_content,view_msd_dataset_contents)

class undetected_msd_logbook(admin.ModelAdmin):
    list_display = ('text','header_category','content_category','language_code')
    # list_display = ('text','category','language_code','language','type')
    list_per_page = 30
    # search_fields = ['category',]
    list_filter = ('language_code','category',)

    def text(self, object):
        return object.text

    def header_category(self, object):
        return object.header_category

    def content_category(self, object):
        return object.content_category

    def language_code(self, object):
        return object.language_code

admin.site.register(undetected_msd_log,undetected_msd_logbook)

class view_ferrero_header(admin.ModelAdmin):
    list_display = ('text','category')
    # list_display = ('text','category','language_code','language','type')
    list_per_page = 30
    # search_fields = ['category',]
    list_filter = ('category',)

    def text(self, object):
        return object.text

    def category(self, object):
        return object.category

admin.site.register(ferrero_header,view_ferrero_header)


class view_general_dataset(admin.ModelAdmin):
    list_display = ('text','category','brand','domain')
    list_per_page = 30
    list_filter = ('category',)

    def text(self, object):
        return object.text

    def category(self, object):
        return object.category

    def brand(self, object):
        return object.brand

    def domain(self, object):
        return object.domain

admin.site.register(general_dataset,view_general_dataset)

# class view_logs(admin.ModelAdmin):
#     formfield_overrides = {
#         models.TextField: {'widget': TextInput(attrs={'rows':10,'size':20000})},
#         models.JSONField: {'widget': Textarea(attrs={'rows':10,'size':20000})},
#     }
#     # list_display = ('date','accounts','input_file','input_body','output')
#     list_display = ('date','accounts','input_file')
#     list_per_page = 30
#     list_filter = ('accounts',)
#     ordering = ('-date',)
#
#     def date(self, object):
#         return object.date
#
#     def accounts(self, object):
#         return object.accounts
#
#     def input_file(self, object):
#         return object.input_file
#
#     # def input_body(self, object):
#     #     return object.input_body
#     #
#     # def output(self, object):
#     #     return object.output
#
# admin.site.register(log_book,view_logs)

class view_logs(admin.ModelAdmin):
    formfield_overrides = {
        models.TextField: {'widget': TextInput(attrs={'rows':10,'size':20000})},
        models.JSONField: {'widget': Textarea(attrs={'rows':10,'size':20000})},
    }
    # list_display = ('date','accounts','input_file','input_body','output')
    list_display = ('date','account_type','account','input_file','error')
    list_per_page = 25
    list_filter = ('date','account_type')
    ordering = ('-date',)

    def date(self, object):
        return object.date

    def account_type(self, object):
        return object.account_type

    def account(self, object):
        if "account" in object.input_body:
            return object.input_body["account"]
        else:
            return "query input not available"

    def input_file(self, object):
        if "file" in object.input_body:
            if object.account_type.lower() == "cep":
                return object.input_body["file"][:100]+"  ....."
            else:
                return object.input_body["file"]
        else:
            return "query input not available"

    def error(self, object):
        return object.error
    #
    # def output(self, object):
    #     return object.output

admin.site.register(logger,view_logs)