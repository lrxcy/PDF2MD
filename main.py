#!/usr/bin/env python3

import math
import io
import os
import time
import base64
import json
import re
import uuid
import sys
import cluster
from cluster import HierarchicalClustering
from cluster import KMeansClustering
from binascii import b2a_hex
from pathlib import Path
from pprint import pprint
from functools import cmp_to_key
import pickle
import shutil
from tqdm import tqdm
import requests
#import pyperclip
import matplotlib.pyplot as plt
from PIL import Image , ImageFont , ImageDraw , ImageEnhance

import redis
import numpy as np
import seaborn as sns

from pdfminer.high_level import extract_pages
from pdfminer.pdfparser import PDFParser
from pdfminer.pdfdocument import PDFDocument
from pdfminer.pdfpage import PDFPage
from pdfminer.pdfinterp import resolve1

from pdfrw import PdfReader, PdfWriter, PageMerge

from sanic import Sanic , response
from sanic.response import json as sanic_json
from sanic.response import text as sanic_text
from sanic_limiter import Limiter, get_remote_address
from werkzeug.utils import secure_filename
import aiofiles

UPLOAD_DIRECTORY = Path.cwd().joinpath( "UPLOAD" )
shutil.rmtree( UPLOAD_DIRECTORY , ignore_errors=True )
UPLOAD_DIRECTORY.mkdir( parents=True , exist_ok=True )

# def read_json( file_path ):
# 	with open( file_path ) as f:
# 		return json.load( f )
# Personal = read_json( "/Users/morpheous/Documents/Misc/CONFIG2/personal/ImageUploadServer/user.json" )
IMAGE_UPLOAD_SERVER_URL = os.environ['IMAGE_UPLOAD_SERVER_URL']
IMAGE_UPLOAD_SERVER_KEY = os.environ['IMAGE_UPLOAD_SERVER_KEY']


def download_file( url , save_path ):
	r = requests.get( url , stream=True )
	total_size = int( r.headers.get( 'content-length' , 0 ) )
	block_size = 1024
	t = tqdm( total=total_size , unit='iB' , unit_scale=True )
	with open( save_path , 'wb' ) as f:
		for data in r.iter_content( block_size ):
			t.update( len( data ) )
			f.write( data )
	t.close()
	if total_size != 0 and t.n != total_size:
		print( "ERROR , something went wrong" )

# Abbreviation Identification / Replacement Can be Tricky
# its not always 1-1 on acronym letters to words
# basal ganglia input receiving motor thalamus (BGMT)

def base64_encode( message ):
	try:
		message_bytes = message.encode( 'utf-8' )
		base64_bytes = base64.b64encode( message_bytes )
		base64_message = base64_bytes.decode( 'utf-8' )
		return base64_message
	except Exception as e:
		print( e )
		return False

class PDFToMD:
	def __init__( self , options={} ):

		# 1.) Init
		self.options = options
		#self.reconnect_redis()
		self.setup_temp_variables()
		self.setup_file_storage()

		# 2.) Analyze
		self.get_meta_data()
		self.get_page_layouts()
		self.get_page_flows()
		self.match_heading_levels_to_fonts_and_sizes()

		# 3.) Generate
		self.generate_md()
		#self.generate_html()
		#self.generate_isolated_linear_structure_pdfs()
		#self.generate_pdf()

	# General Utilities
	# =================================================================

	def write_text( self , file_path , text_lines_list ):
		#with open( file_path , 'a', encoding='utf-8' ) as f:
		with open( file_path , 'w', encoding='utf-8' ) as f:
			f.writelines( text_lines_list )

	def read_text( self , file_path ):
		with open( file_path ) as f:
			return f.read().splitlines()

	def base64_encode( self , message ):
		try:
			message_bytes = message.encode( 'utf-8' )
			base64_bytes = base64.b64encode( message_bytes )
			base64_message = base64_bytes.decode( 'utf-8' )
			return base64_message
		except Exception as e:
			print( e )
			return False

	def base64_decode( self , base64_message ):
		try:
			base64_bytes = base64_message.encode( 'utf-8' )
			message_bytes = base64.b64decode(base64_bytes)
			message = message_bytes.decode( 'utf-8' )
			return message
		except Exception as e:
			print( e )
			return False

	def most_common( self , input_list ):
		return max( set( input_list ) , key=input_list.count )


	def determine_image_type( self , stream_first_4_bytes ):
		file_type = None
		bytes_as_hex = b2a_hex( stream_first_4_bytes ).decode()
		if bytes_as_hex.startswith( 'ffd8' ):
			file_type = '.jpeg'
		elif bytes_as_hex == '89504e47':
			file_type = '.png'
		elif bytes_as_hex == '47494638':
			file_type = '.gif'
		elif bytes_as_hex.startswith('424d'):
			file_type = '.bmp'
		return file_type

	# https://stackoverflow.com/a/25736515
	def convert_to_sentences( self , text_blob ):
		return re.split( r'(?<=[^A-Z].[.?]) +(?=[A-Z])' , text_blob )

	def convert_to_bullitize_list( self , input_text ):
		input_text = " ".join( input_text.split() )
		sentences = self.convert_to_sentences( input_text )
		bulleted_line_list = [ f"- {x}"  for x in sentences ]
		#bulleted_line_list_raw_markdown = "\n".join( bulleted_line_list )
		#bulleted_line_list_raw_markdown += "\n"
		#return bulleted_line_list_raw_markdown
		return bulleted_line_list

	def reconnect_redis( self ):
		self.redis = redis.StrictRedis(
			host= "127.0.0.1" ,
			port="6379" ,
			db=3 ,
			)

	def get_clusters( self , input_list , number_of_clusters=3 ):

		# 1.) Reshape for KMeans
		input_list = [ ( 0 , x ) for x in input_list ]

		# 2.) Magic
		clusterer = KMeansClustering( input_list )
		clusters = clusterer.getclusters( number_of_clusters )

		# 3.) Reshape Back to Normal and Sort Highest To Lowest
		temp = []
		for index , cluster in enumerate( clusters ):
			x1 = [ x[1] for x in cluster ]
			temp.append( sorted( x1 , reverse=True ) )

		clusters = sorted( temp , reverse=True , key=lambda x: x[0] )
		return clusters

	def convert_pil_image_to_b64_md_string( self , image ):
		buffered = io.BytesIO()
		#image.save( buffered , format=image.format )
		image.save( buffered , format="JPEG" )
		image_bytes = buffered.getvalue()
		base64_bytes = base64.b64encode( image_bytes )
		base64_string = base64_bytes.decode()
		#image_string = f"data:image/jpeg;base64,{base64_string}"
		md_string = f'<img src="data:image/jpeg;base64,{base64_string}">'
		return md_string

	# How to Make New Keys
	# 1.) Make Username and Password
	# ${string:position:length}
	# pwgen -1 34 | shasum -a 256 | awk '{ print $1; }' | while read x ; do echo "${x:0:32}" ; echo "${x:32:64}" ; done
	# 2.) Make Cookie and JWT Secrets
	# pwgen -1 34 | shasum -a 256 | awk '{ print $1; }'
	# pwgen -1 34 | shasum -a 256 | awk '{ print $1; }' | while read x ; do echo "${x:0:32}" ; echo "${x:32:64}" ; done && pwgen -1 34 | shasum -a 256 | awk '{ print $1; }' && pwgen -1 34 | shasum -a 256 | awk '{ print $1; }'
	def upload_image( self , image ):
		buffered = io.BytesIO()
		image.save( buffered , format="JPEG" )
		image_bytes = buffered.getvalue()
		file_list = { "file": image_bytes }
		headers = { 'key': IMAGE_UPLOAD_SERVER_KEY }
		response = requests.post( IMAGE_UPLOAD_SERVER_URL , headers=headers , files=file_list )
		response.raise_for_status()
		return f"![]({response.text})"

	# General Utilities
	# =================================================================

	# Class Utilities
	# =================================================================

	def setup_temp_variables( self ):
		self.pages = []
		self.bounding_boxes = {}

	def setup_file_storage( self ):
		self.file_path = self.options["file_path"]
		self.file_path_posix = Path( self.file_path )
		self.output_md_file_path_posix = self.file_path_posix.parent.joinpath( f"{self.file_path_posix.stem}.md" )
		self.output_html_file_path_posix = self.file_path_posix.parent.joinpath( f"{self.file_path_posix.stem}.html" )
		self.output_pdf_file_path_posix = self.file_path_posix.parent.joinpath( f"{self.file_path_posix.stem}-Cleaned.pdf" )
		#self.temp_directory = tempfile.gettempdir()
		self.temp_directory_posix = self.file_path_posix.parent.joinpath( f"{self.file_path_posix.stem}-Temp" )
		shutil.rmtree( self.temp_directory_posix , ignore_errors=True )
		self.temp_directory_posix.mkdir( parents=True , exist_ok=True )

	def get_id( self , one , two , three , four ):
		return self.base64_encode( f"{one:.3f}-{two:.3f}-{three:.3f}-{four:.3f}" )

	def get_meta_data( self ):
		self.file = open( self.file_path , 'rb' )
		self.parser = PDFParser( self.file )
		self.document = PDFDocument( self.parser )
		self.total_pages = resolve1( self.document.catalog['Pages'] )['Count']

	def sort_elements_on_y_axis( self , elements , reverse=True ):
		return sorted( elements , reverse=reverse , key=lambda x: x['bounding_box']['y2'] )

	def sort_elements_on_x_axis( self , elements , reverse=False ):
		if len( elements ) < 2:
			return elements
		print( len( elements ) )
		SIDE_BY_SIDE_HEIGHT_THRESHOLD = 50
		SIDE_BY_SIDE_WIDTH_THRESHOLD = 50
		# Trying to Find Small Y-Distance AND Large X-Distance
		Y_DISTANCE_MIN = 3 # at least as large as smallest font size
		Y_DISTANCE_MAX = 25
		X_DISTANCE_MIN = 50
		X_DISTANCE_MAX = 999999
		results = elements
		#for index , element in enumerate( results[1:] ):
		for index in range( 1 , len( results ) + 1 ):
			#id = self.get_id( element['bounding_box']['x1'] , element['bounding_box']['y1'] , element['bounding_box']['x2'] , element['bounding_box']['y2'] )]
			#print( type( results[ index ] ) )
			try:
				a = results[ index ]
				b = results[ index - 1 ]
			except Exception as e:
				print( f"[{index}] of {len(results)}" )
				return elements

			a_height = abs( a['bounding_box']['y2'] - a['bounding_box']['y1'] )
			b_height = abs( b['bounding_box']['y2'] - b['bounding_box']['y1'] )
			height_distance = abs( b_height - a_height ) # closer it is to zero , the more similar they are
			a_width = abs( a['bounding_box']['x2'] - a['bounding_box']['x1'] )
			b_width = abs( b['bounding_box']['x2'] - b['bounding_box']['x1'] )
			width_distance = abs( b_width - a_width )

			y1 = a['bounding_box']['y2']
			y2 = b['bounding_box']['y2']
			y_distance = abs( y2 - y1 )

			x1 = a['bounding_box']['x1']
			x2 = b['bounding_box']['x1']
			x_distance = abs( x2 - x1 )

			if y_distance > Y_DISTANCE_MIN and y_distance < Y_DISTANCE_MAX:
				if x_distance > X_DISTANCE_MIN and x_distance < X_DISTANCE_MAX:
					# We Supposedly Found Side-By-Side Bounding Boxes

					print( f"{height_distance} === {width_distance}" )

					# But now we must make sure its not just continuation from previous block
					# Compare Y-Lengths
					if height_distance > SIDE_BY_SIDE_HEIGHT_THRESHOLD:
						continue
					# Compare X-Length to see if we are in side-by-side columns
					if width_distance < SIDE_BY_SIDE_WIDTH_THRESHOLD:
						continue

					# print( f"[{a['text_preview']}] vs [{b['text_preview']}] === Y-Difference === {y_distance} === X-Difference === {x_distance}" )
					# Swapum
					results[ index - 1 ] , results[ index ] = results[ index ] , results[ index - 1 ]

					# Merge if Only Texts
					if results[ index - 1 ][ "type" ] == "paragraph" and results[ index ][ "type" ] == "paragraph":

						results[ index - 1 ][ "text" ] = results[ index - 1 ][ "text" ] + results[ index ][ "text" ]
						results[ index - 1 ][ "text_cleaned" ] = results[ index - 1 ][ "text" ].replace( '\n' , ' ' ).replace( '\r' , '' )
						del results[ index ]

		return results

	def crop_pdf_page( self , options ):
		output = PdfWriter( options[ "output_file_path" ] )
		page = PdfReader( options[ "input_file_path" ] ).pages[ options[ "page_number" ] ]
		cropped = page
		cropped['/MediaBox'][ 0 ] = options[ "bounding_box" ][ "upper_left" ] - options[ "padding" ]
		cropped['/MediaBox'][ 1 ] = options[ "bounding_box" ][ "upper_right" ] - options[ "padding" ]
		cropped['/MediaBox'][ 2 ] = options[ "bounding_box" ][ "lower_left" ] + options[ "padding" ]
		cropped['/MediaBox'][ 3 ] = options[ "bounding_box" ][ "lower_right" ] + options[ "padding" ]
		output.addPage( cropped )
		output.write()

	def get_font_sizes( self ):
		self.font_sizes = []
		temp = []
		for page_index , page in enumerate( self.page_flows ):
			for element_index , element in enumerate( page ):
				if element[ "type" ] != "paragraph":
					continue
				temp.append( element["size"] )
		temp = sorted( temp , reverse=True )
		temp = list( dict.fromkeys( temp ) )
		self.font_sizes = temp

	def get_headings( self ):
		#self.heading_map = { "h1": None , "h2": None , "h3": None , "h4": None , "h5": None , "h6": None , "text": None }
		for page_index , page in enumerate( self.page_flows ):
			for element_index , element in enumerate( page[ 1:-1 ] ):
				if element[ "type" ] == "paragraph":

					# 0.) Quick Pointers
					m1 = self.page_flows[ page_index ][ element_index - 1 ]
					x = self.page_flows[ page_index ][ element_index ]
					p1 = self.page_flows[ page_index ][ element_index + 1 ]

					# 1.) Thats all nice and whatever , but just look at bolds
					if "font" in x:
						if x["font"][ -2: ] == ".B":
							self.page_flows[ page_index ][ element_index ][ "type" ] = "heading"

					# 2.) Get Word Total's and Distances Between Sandwhiched Bounding Boxes
					# m1_total_words = len( m1["text"].split() )
					# x_total_words = len( x["text"].split() )
					# p1_total_words = len( p1["text"].split() )
					# x_m1_distance = abs( x_total_words - m1_total_words )
					# x_p1_distance = abs( p1_total_words - x_total_words )
					# total_word_count_distance = abs( p1_total_words - x_total_words - m1_total_words )
					# print( f"{str(x_m1_distance).zfill(3)} === {str(x_total_words).zfill(3)} === {str(x_p1_distance).zfill(3)} === Word Count Distance: {str(x_p1_distance).zfill(3)} === Bold: {is_bold} === {x['text_preview']}" )

					#element[ "type" ] = "heading":

	# Class Utilities
	# =================================================================


	# PDF Structure Analysis
	# =================================================================

	def get_page_layouts( self ):
		generator = extract_pages( self.file_path )
		print( "Scanning Page Layouts" )
		self.page_layouts = []
		for page_layout in tqdm( generator , total=self.total_pages ):
			self.page_layouts.append( page_layout )

	def get_paragraph_info( self , text_box ):
		# height = text_box.height
		# width = text_box.width
		# pprint( vars( text_box ) )
		global_fonts = []
		global_sizes = []
		lines = []
		for text_line_index , text_line in enumerate( text_box ):
			fonts = []
			sizes = []
			for line_element_index , line_element in enumerate( text_line ):
				line_element_class = type( line_element ).__name__
				if line_element_class == "LTChar":
					fonts.append( line_element.fontname )
					sizes.append( line_element.size )
				elif line_element_class == "LTAnno":
					pass
				else:
					#print( line_element_class )
					pass
			most_common_font = self.most_common( fonts )
			most_common_size = self.most_common( sizes )
			global_fonts.append( most_common_font )
			global_sizes.append( most_common_size )
			lines.append({
					"text": text_line.get_text() ,
					"font": most_common_font ,
					"size": most_common_size
				})
		bounding_box_id = self.get_id( text_box.x0 , text_box.y0 , text_box.x1 , text_box.y1 )
		data = {
			"id": bounding_box_id ,
			"type": "paragraph" ,
			"text": text_box.get_text() ,
			"text_preview": text_box.get_text().replace( '\n' , ' ' ).replace( '\r' , '' )[0:40] ,
			"text_cleaned": text_box.get_text().replace( '\n' , ' ' ).replace( '\r' , '' ) ,
			"lines": lines ,
			"font": self.most_common( global_fonts ) ,
			"size": round( self.most_common( global_sizes ) , 1 ) ,
			"padding": 5 ,
			"bounding_box": {
				"x1": text_box.x0 ,
				"y1": text_box.y0 ,
				"x2": text_box.x1 ,
				"y2": text_box.y1 ,
			}
		}
		self.bounding_boxes[ bounding_box_id ] = data
		return data

	def get_image_info( self , element ):
		print( "LTFigure" )
		image = None
		try:
			#"test_bytes": element._objs[ 0 ].stream.rawdata
			#"stream": element._objs[ 0 ].stream
			image = Image.open( io.BytesIO( element._objs[ 0 ].stream.rawdata ) )
		except Exception as e:
			return False
		image_md_string = self.upload_image( image )
		#image_md_string = self.convert_pil_image_to_b64_md_string( image )
		#image.show()
		bounding_box_id = self.get_id( element._objs[ 0 ].x0 , element._objs[ 0 ].y0 , element._objs[ 0 ].x1 , element._objs[ 0 ].y1 )
		image_info = {
			"id": bounding_box_id ,
			"type": "image" ,
			"width": element._objs[ 0 ].width ,
			"height": element._objs[ 0 ].height ,
			"bounding_box": {
				'x1': element._objs[ 0 ].x0 , 'y1': element._objs[ 0 ].y0 ,
				'x2': element._objs[ 0 ].x1 , 'y2': element._objs[ 0 ].y1 ,
			} ,
			"md_string": image_md_string
		}
		#pprint( image_info )
		self.bounding_boxes[ bounding_box_id ] = image_info
		return image_info

		# pprint( vars( element._objs[ 0 ] ) )
		# element._objs[ 0 ] == <class 'pdfminer.layout.LTImage'> ==
			# {'x0': 141.505, 'y0': 220.479, 'x1': 453.912, 'y1': 737.008, 'width': 312.407, 'height': 516.529, 'bbox': (141.505, 220.479, 453.912, 737.008), 'name': 'Im9', 'stream': <PDFStream(462): raw=122276, {'Length': 122274, 'Filter': /'DCTDecode', 'Width': 651, 'Height': 1077, 'BitsPerComponent': 8, 'ColorSpace': <PDFObjRef:983>, 'Intent': /'Perceptual', 'Type': /'XObject', 'Subtype': /'Image'}>, 'srcsize': (651, 1077), 'imagemask': None, 'bits': 8, 'colorspace': [<PDFObjRef:983>]}

		# type( element._objs[ 0 ].stream ) == # class 'pdfminer.pdftypes.PDFStream'
		#print( vars( element._objs[ 0 ].stream ) )

		#element._objs[ 0 ].stream.decode()
		#print( element._objs[ 0 ].stream.rawdata[ 0 : 4 ] )
		#print( b2a_hex( element._objs[ 0 ].stream.rawdata[ 0 : 4 ] ).decode() )

	def get_paragraphs_and_images( self , page_layout ):
		images = []
		paragraphs = []
		for index , element in enumerate( page_layout ):
			class_name = type(element).__name__
			if class_name == "LTTextBoxHorizontal":
				pargraph_info = self.get_paragraph_info( element )
				paragraphs.append( pargraph_info )
			elif class_name == "LTRect":
				#print( "LTRect" )
				#print( element )
				pass
			elif class_name == "LTFigure":
				image_info = self.get_image_info( element )
				if image_info != False:
					images.append( image_info )
			elif class_name == "LTCurve":
				pass
			elif class_name == "LTLine":
				pass
			else:
				print( class_name )

		return images + paragraphs

	def get_page_flows( self ):
		self.page_flows = []
		for page_index , page_layout in enumerate( self.page_layouts ):
			# 1.) Find Paragraph and Image Page Elements
			paragraphs_and_images_unsorted = self.get_paragraphs_and_images( page_layout )
			self.page_flows.append( paragraphs_and_images_unsorted )

			# # 2.) Sort Bounding Boxes Top-To-Bottom from Upper Left Coordinate
			# sorted_elements = self.sort_elements_on_y_axis( paragraphs_and_images_unsorted )

			# # 3.) Sort Bounding Boxes Left-To-Right from Lower Left Coordinate
			# sorted_elements = self.sort_elements_on_x_axis( sorted_elements )
			# self.page_flows.append( sorted_elements )

	def match_heading_levels_to_fonts_and_sizes( self ):

		# 1.) Get Font Size Range
		self.get_font_sizes()
		total_sizes = len( self.font_sizes )
		if total_sizes <= 3:
			total_size_clusters = 3
		else:
			if total_sizes >= 8:
				total_size_clusters = 4
			else:
				total_size_clusters = 3
		self.font_size_clusters = self.get_clusters( self.font_sizes , total_size_clusters )
		pprint( self.font_sizes )
		pprint( self.font_size_clusters )

		# 2.) Try to Predict If Something Is heading or not based on [boldness] , number of words , size , position , etc
		self.get_headings()

		# 3.) Assign

		if len( self.font_size_clusters ) < 3:
			print( "Largest Font Size is just Heading" )
			print( "Everything Else is just text" )
			print( "Just ignore this case for now" )
			return

		# 3.B.) For Everything Else , if its a
		for page_index , page in enumerate( self.page_flows ):
			for element_index , element in enumerate( page ):
				# 3.A.) Automatically Assign Largest Font Cluster to H1's
				if element[ "type" ] == "paragraph":
					if element["size"] in self.font_size_clusters[ 0 ]:
						element["heading_level"] = "h1"
						continue
					if element[ "type" ] == "heading":
						if element["size"] in self.font_size_clusters[ 1 ]:
							element["heading_level"] = "h2"

	# PDF Structure Analysis
	# =================================================================

	# Generation
	# =================================================================

	def generate_isolated_linear_structure_pdfs( self ):
		index = 1
		for page_index , page in enumerate( self.page_flows ):
			for element_index , element in enumerate( page ):
				output_file_path = self.temp_directory_posix.joinpath( f"{str(index).zfill(3)}-{self.file_path_posix.stem }-{str(page_index).zfill(2)}-{str(element_index).zfill(2)}.pdf" )
				id = self.get_id( element[ "bounding_box" ][ "x1" ] , element[ "bounding_box" ][ "y1" ] , element[ "bounding_box" ][ "x2" ] , element[ "bounding_box" ][ "y2" ] )
				self.crop_pdf_page({
					"id": id ,
					"page_index": page_index ,
					"element_index": element_index ,
					"input_file_path": str( self.file_path ) ,
					"output_file_path": str( output_file_path ) ,
					"page_number": page_index ,
					"padding": 1 ,
					"bounding_box": {
						"upper_left": element[ "bounding_box" ][ "x1" ] ,
						"upper_right": element[ "bounding_box" ][ "y1" ] ,
						"lower_left": element[ "bounding_box" ][ "x2" ] ,
						"lower_right": element[ "bounding_box" ][ "y2" ] ,
					}
				})
				self.bounding_boxes[ id ][ "output_file_path" ] = str( output_file_path )
				index += 1

	def generate_md( self ):
		md_lines = []
		heading_levels = { "h1": "#" , "h2": "##" , "h3": "###" , "h4": "####" , "h5": "#####" , "h6": "######" }
		self.md_html = "<html><body>"
		for page_index , page in enumerate( self.page_flows ):
			for element_index , element in enumerate( page ):
				if element[ "type" ] == "heading":
					if "heading_level" in element:
						#md_lines += f"<{element['heading_level']}>{element['text_cleaned']}</{element['heading_level']}/>\n\n"
						md_lines += f"{heading_levels[element['heading_level']]} {element['text_cleaned']}\n\n"
						self.md_html += f"<p>{heading_levels[element['heading_level']]} {element['text_cleaned']}</p>"
					else:
						md_lines += f"**{element['text_cleaned']}**\n"
						self.md_html += f"** {element['text_cleaned']}"
				elif element[ "type" ] == "paragraph":
					#md_lines.append( f'''<p>{element["text"]}</p>''' )
					bulletized_lines = self.convert_to_bullitize_list( element["text"] )
					md_lines += bulletized_lines
					md_lines += "\n\n"
					for bullet_index , bullet_line in enumerate( bulletized_lines ):
						self.md_html += f"<p>{bullet_line}</p>"
				elif element[ "type" ] == "image":
					md_lines += element["md_string"] + "\n\n"
					self.md_html += element["md_string"]
				elif element[ "type" ] == "equation":
					pass
		self.md_lines = md_lines
		# self.html = "<html><body>"
		# for index , line in enumerate( self.md_lines ):
		# 	self.html += f"<p>{line}</p>"
		# self.html += "</body></html>"
		#self.md = "\n\n".join( md_lines )
		#print( md )
		#self.write_text( str( self.output_md_file_path_posix ) , md_lines )

	# Generation
	# =================================================================

#app = Sanic( name="PDF To MD Server" )
#limiter = Limiter( app , key_func=get_remote_address )
#app.route( "/pdf2md/" , methods=['POST'] )
#@limiter.limit( "2/minute" )

from flask import Flask , render_template , request , redirect
app = Flask( "PDF To MD Server" )

@app.route( '/pdf2md' , methods=[ 'GET' ] )
def home():
	return redirect( "https://39363.org/pdf2md/form" )

@app.route( '/pdf2md/form' , methods=[ 'GET' ] )
def pdf2md_form():
	upload_form_html = '''
		<html>
			<head>
				<title>PDF To MD</title>
			</head>
			<body>
				<form action="https://39363.org/pdf2md/uploader" method="POST" enctype="multipart/form-data">
					<label for="file">PDF:</label>
					<input type="file" name="file" id="file"><br>
					<input type="submit" value="Upload">
				</form>
			</body>
		</html>
	'''
	return upload_form_html

#@app.route( '/pdf2md/url/<path:url_path>' , methods=[ 'GET' ] )
@app.route( '/pdf2md/<path:url_path>' , methods=[ 'GET' ] )
def pdf2md_url( url_path ):
	print( f"here at /pdf2md/<{url_path}>" )
	try:
		print( "Downloading" )
		file_path_posix = UPLOAD_DIRECTORY.joinpath( f"{uuid.uuid4()}.pdf" )
		file_path_string = str( file_path_posix )
		download_file( url_path , file_path_string )
		print( "Converting" )
		x = PDFToMD({ "file_path": file_path_string })
		file_path_posix.unlink()
		return x.md_html
	except Exception as e:
		print( e )
		return "Failed"

@app.route( '/pdf2md/uploader' , methods=[ 'POST' ] )
def pdf2md_upload():
	try:
		print( "here" )
		file = request.files['file']
		#print( file )
		# 1.) Get Filename Info
		# try:
		# 	file = request.files.get("file")
		# except Exception:
		# 	return json({"Received": False})
		# pprint( file )
		# upload_file = request.files.get( 'file_names' )
		# if not upload_file:
		# 	return response.redirect( "/?error=no_file" )
		file_name = secure_filename( file.filename )
		file_name_parts = file_name.split( "." )
		file_name_stem = file_name_parts[ 0 ]
		file_name_stem_b64 = base64_encode( file_name_stem )
		file_type = file_name_parts[ 1 ]

		# 2.) Prepare Upload Directory
		# upload_path_basedir = UPLOAD_DIRECTORY.joinpath( file_name_stem )
		# shutil.rmtree( upload_path_basedir , ignore_errors=True )
		# upload_path_basedir.mkdir( parents=True , exist_ok=True )
		file_path = UPLOAD_DIRECTORY.joinpath( f"{file_name_stem_b64}.pdf" )
		print( str( file_path ) )
		# Save File
		# async with aiofiles.open( str( file_path ) , 'wb' ) as f:
		# 	await f.write( upload_file.body )
		# 	x = PDFToMD({ "file_path": str( file_path ) })
		# 	return sanic_text( x.md )
		print( "Uploading" )
		file.save( str( file_path ) )
		print( "Converting" )
		x = PDFToMD({ "file_path": str( file_path ) })
		file_path.unlink()
		return x.md_html
	except Exception as e:
		print( e )
		return "failed"


app.run( host="0.0.0.0" , port='9454' ) # For Docker
#app.run( host="127.0.0.1" , port='9454' ) # For LocalHost / Caddy Standalone