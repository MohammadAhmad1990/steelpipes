import frappe
import mysql.connector
import json
import xlsxwriter
import time
import io
from datetime import date,datetime
from string import ascii_uppercase
from frappe.utils import get_site_name,get_site_info,get_site_base_path,get_site_path,get_files_path,get_bench_path,get_site_url,get_datetime

@frappe.whitelist()
def get_charges_account(steel_pipes_charges_settings):
    charges_doc = frappe.get_doc(steel_pipes_charges_settings)
    return {'loading_head': charges_doc.loading_account_head, 'cutting_labor_head': charges_doc.cutting_labor_account_head, 'transport_head': charges_doc.transport_account_head}


# Pipe Stock Summary Sheet
@ frappe.whitelist()
def get_pipe_stock(warehouse):
    # Connecting to database
    report_settings = frappe.get_doc('Pipe Stock Summary Setting')
    mydb = mysql.connector.connect(
        host=report_settings.host,
        user=report_settings.user,
        passwd=report_settings.password
    )
    xlsx_name = '/tmp/pipstocksheet-{0}.xlsx'.format(warehouse)
    workbook = xlsxwriter.Workbook(xlsx_name)                                   # Creating file
    worksheet = workbook.add_worksheet(name=warehouse)                                          # Creating Worksheet
    worksheet.set_column(1, 24, 6)                                                              # Setting column width
    border = workbook.add_format()
    border.set_align('center')
    border.set_align('vcenter')
    border.set_border()
    for row in range(0,61,1):
        for column in range(0,24,1):
            worksheet.write(row,column,None,border)
    # Setting Formats
    bold = workbook.add_format({'bold': True})
    bold.set_border()
    format6 = workbook.add_format({'num_format': 'dd/mm/yyyy hh:mm AM/PM','bold':True})
    merge_format = workbook.add_format({'align': 'center','bold':True})
    merge_format.set_border()
    
    worksheet.write('A1', str(warehouse),bold)
    now = datetime.now()
    worksheet.write('F1', now.strftime("%B %d, %Y %H:%M:%S"),format6)
    cellTitle = 0
    cellTitlerow = 2
    cellThickness = ''
    cellLength = ''
    cellQty = ''
    cellWeight = ''
    # worksheet.write('A1', 'Hello world')

    id_num = 0
    sizes = ['1/2 INCH','3/4 INCH','1 INCH','1 1/4 INCH','1 1/2 INCH','2 INCH','2 1/2 INCH','3 INCH','4 INCH','5 INCH','6 INCH','7 INCH','8 INCH','10 INCH','12 INCH']
    size_id = ['pipe1_2inch','pipe3_4inch','pipe1inch','pipe11_4inch','pipe11_2inch','pipe2inch','pipe21_2inch','pipe3inch','pipe4inch','pipe5inch','pipe6inch','pipe7inch','pipe8inch','pipe10inch','pipe12inch']
    callbackreturn = {}
    for pipe_size in sizes:
        # print(pipe_size)
        i = 0 
        
        mycursor = mydb.cursor()
        mycursor.execute('''SELECT item_code,warehouse,actual_qty FROM {0}.tabBin WHERE item_code LIKE 'Pipe-MS-{1}%' AND actual_qty>0 AND warehouse LIKE "{2}"'''.format(report_settings.database,pipe_size,warehouse))
        myresult = mycursor.fetchall()
        if (myresult):
            tempTitle = ascii_uppercase[cellTitle] +str(cellTitlerow)
            worksheet.write(tempTitle, pipe_size,bold)
            mergetitle = ascii_uppercase[cellTitle] +str(cellTitlerow) + ':' + ascii_uppercase[cellTitle+3] +str(cellTitlerow)
            worksheet.merge_range(mergetitle, pipe_size, bold)
            worksheet.write(ascii_uppercase[cellTitle]+str(cellTitlerow+1), 'MM',bold)
            worksheet.write(ascii_uppercase[cellTitle+1]+str(cellTitlerow+1), 'FEET',bold)
            worksheet.write(ascii_uppercase[cellTitle+2]+str(cellTitlerow+1), 'QTY',bold)
            worksheet.write(ascii_uppercase[cellTitle+3]+str(cellTitlerow+1), 'KG',bold)
            
            callbackreturn[size_id[id_num]] = {}
            for x in myresult:

                sqlstr = """SELECT attribute_value FROM {0}.`tabItem Variant Attribute` 
                            WHERE parent LIKE '{1}' 
                            AND attribute LIKE 'Thickness (mm)'""".format(report_settings.database,x[0])
                mycursor.execute(sqlstr)
                thickness = mycursor.fetchone()

                sqlstr = """SELECT attribute_value FROM {0}.`tabItem Variant Attribute` 
                            WHERE parent LIKE '{1}' 
                            AND attribute LIKE 'Length (feet)'""".format(report_settings.database,x[0])
                mycursor.execute(sqlstr)
                length = mycursor.fetchone()
                item = frappe.get_doc('Item',x[0])
                pipe_weight = '-'
                for w in item.receiving_details:
                    if w.receiving_warehouse == warehouse:
                        pipe_weight = w.scale_weight
                callbackreturn[size_id[id_num]][i] = {'thickness': str(thickness[0]), 'length': str(length[0]), 'qty': str(round(x[2],2)), 'weight': pipe_weight}
                worksheet.write(ascii_uppercase[cellTitle]+str(cellTitlerow+2 + i), (float(thickness[0])),border)
                worksheet.write(ascii_uppercase[cellTitle+1]+str(cellTitlerow+2 + i), (float(length[0])),border)
                worksheet.write(ascii_uppercase[cellTitle+2]+str(cellTitlerow+2 + i), (round(x[2],2)),border)
                worksheet.write(ascii_uppercase[cellTitle+3]+str(cellTitlerow+2 + i), pipe_weight,border)
                i += 1
            cellTitle +=4
            if cellTitle == 24:
                cellTitle = 0
                cellTitlerow +=30
        id_num +=1
    callbackreturn = json.dumps(callbackreturn)

    workbook.close()
    return callbackreturn

@frappe.whitelist()
def generate_xlsx_item_stock(warehouse):
    file = io.open('/tmp/pipstocksheet-{0}.xlsx'.format(warehouse), "rb", buffering = 0)
    data = file.read()
    if not data:
        frappe.msgprint(('No Data'))
        return
    frappe.local.response.filecontent = data
    frappe.local.response.type = "download"
    frappe.local.response.filename = "pipestocksheet-{0}.xlsx".format(warehouse)

def update_delivered_item_weight_statistics(self,cdt):
    for d in self.items:
        if 'Pipe-MS' in str(d.item_code):
            item = frappe.get_doc('Item',d.item_code)
            item.db_set('last_weight_delivered',d.scale_weight_um)
            item.db_set('last_quantity_delivered',d.qty)

def update_received_item_weight_statistics(self,cdt):
    for d in self.items:
        if 'Pipe-MS' in str(d.item_code):
            item = frappe.get_doc('Item',d.item_code)
            item.db_set('last_weight_received',d.scale_weight_um)
            item.db_set('last_quantity_received',d.qty)

def create_strip_width(attribute,thickness,step,width):
    while (thickness< 8.05):
                attribute.append('item_attribute_values', {
                    'attribute_value': str(width),
                    'abbr': str(width) + ' MM' 
                })
                thickness += 0.05
                step +=1
                if step == 10:
                    step = 1
                    width -=1

def create_pipe_ms_items():
    item_group = frappe.new_doc('Item Group')
    item_group.item_group_name = 'Pipes'
    item_group.show_in_website = 1
    item_group.save()
    # Creating required attributes
    # Size (inches)
    attribute = frappe.new_doc('Item Attribute')
    attribute.attribute_name = 'Size (inches)'
    sizes = ['1/2','3/4','1','1 1/4','1 1/2','2','2 1/2','3','4','5','6','7','8','10','12']
    for size in sizes:
        attribute.append('item_attribute_values', {
            'attribute_value': size,
            'abbr': size + ' INCH'
        })
    attribute.save()

    # Material Type
    attribute = frappe.new_doc('Item Attribute')
    attribute.attribute_name = 'Material Type'
    attribute.append('item_attribute_values', {
        'attribute_value': 'MILD STEEL',
        'abbr': 'MS'
    })
    attribute.save()

    # Thickness (mm)
    attribute = frappe.new_doc('Item Attribute')
    attribute.attribute_name = 'Thickness (mm)'
    thickness = 1
    while thickness<8.05:
        attribute.append('item_attribute_values', {
            'attribute_value': str(thickness),
            'abbr': str(thickness) + ' MM'
        })
        thickness += 0.05
    attribute.save()

    # Length
    attribute = frappe.new_doc('Item Attribute')
    attribute.attribute_name = 'Length (feet)'
    attribute.append('item_attribute_values', {
            'attribute_value': '20',
            'abbr': '20 FT'
        })
    attribute.append('item_attribute_values', {
            'attribute_value': '10',
            'abbr': '10 FT'
        })
    attribute.save()

    # Outer Diameter
    attribute = frappe.new_doc('Item Attribute')
    attribute.attribute_name = 'Outer Diameter'
    ODs = ['26.7','33.5','42','48','60.3','76','88','113','140','165','190','216','266.5','324']
    for OD in ODs:
        attribute.append('item_attribute_values', {
            'attribute_value': OD,
            'abbr': 'OD ' + OD 
        })
    attribute.save()

    # Width (mm)
    attribute = frappe.new_doc('Item Attribute')
    attribute.attribute_name = 'Width (mm)'
    for OD in ODs:
        thickness = 1
        step = 1
        if OD == '26.7':
            width = 81
            create_strip_width(attribute,thickness,step,width)
        elif OD == '33.5':
            width = 102
            create_strip_width(attribute,thickness,step,width)
        elif OD == '42':
            width = 129
            create_strip_width(attribute,thickness,step,width)
        elif OD == '48':
            width = 148
            create_strip_width(attribute,thickness,step,width)
        elif OD == '60.3':
            width = 186
            create_strip_width(attribute,thickness,step,width)
        elif OD == '76':
            width = 236
            create_strip_width(attribute,thickness,step,width)
        elif OD == '88':
            width = 273
            create_strip_width(attribute,thickness,step,width)
        elif OD == '113':
            width = 352
            create_strip_width(attribute,thickness,step,width)
        elif OD == '140':
            width = 437
            create_strip_width(attribute,thickness,step,width)
        elif OD == '165':
            width = 515
            create_strip_width(attribute,thickness,step,width)
        elif OD == '190':
            width = 594
            create_strip_width(attribute,thickness,step,width)
        elif OD == '216':
            width = 676
            create_strip_width(attribute,thickness,step,width)
        elif OD == '266.5':
            width = 834
            create_strip_width(attribute,thickness,step,width)
        elif OD == '324':
            width = 1015
            create_strip_width(attribute,thickness,step,width)
    attribute.save()

    # Making Pipe Products
    