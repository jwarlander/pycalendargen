#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#   PyCalendarGen.py - Copyright (C) 2005-2012 Johan Wärlander
#
#   This file is part of PyCalendarGen.
#
#   PyCalendarGen is free software; you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation; either version 2 of the License, or
#   (at your option) any later version.
#
#   PyCalendarGen is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with PyCalendarGen; if not, write to the Free Software
#   Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#
#
# Generate calendar in PDF format.
#
# The program loads special days like holidays, namedays, birthdays etc
# from a file called "days_[lang].txt". For example, the language code
# for English (American) is enA, so the file would be "days_enA.txt".
#
# This file MUST be in UTF-8 if it contains non-ASCII characters, and
# has the following format:
#
#   DD.MM [color:]Text to appear [ / [color:]Additional line for same day ]
#
# Examples:
#
#   25.3 John's Birthday
#    -> would show in black, as a single entry, for March 25
#   25.3 John's Birthday / Start of vacation!
#    -> would show in black, as two entries below each other, for March 25
#   25.3 2:John's Birthday / Start of vacation!
#    -> would display John's Birthday in cyan (color code 2), and then on
#       the next line Start of vacation! in black
#   25.3 1:John's Birthday
#    -> would display John's Birthday in red (color code 1), and make March
#       25 a red day on the calendar page. This is how holidays are tagged
#       in the special day file.
#
# Dependencies
# ============
#  o ReportLab (http://www.reportlab.org/)
#  o eGenix mxDateTime (http://www.egenix.com/)
#
# TODO
# ====
#  o Improve calendar rendering structure to allow for styles
#    - modules will implement renderBackground(), renderGrid(), renderForeground()
#    - renderGrid() will be called with all days as a list, each day being a tuple
#      that is filled out like this:
#        (day_number, day_color, ((item_name, item_color), (item_name, item_color), ..))
#    - this means renderGrid() will ONLY need to worry about how to -display- the data
#  o Possibly move day_table functionality directly to data file being loaded
#  o Command-line option for setting language
#  o Packages for common Linux distributions
#  o Allow rendering of single PDF for the full year (or any span of months)
#  o Integrate rendering of opposite pages with images
#    - refer to directory, pick image files in alphabetical order
#    - scale images to full page, optionally with border
#    - allow for captions, possibly using <image_name>.txt as input
#  o Improve font handling
#    - command-line option for selecting font(s)?
#    - maybe allow for usage of system fonts
#  o Allow specification of a config file for all rendering options
#    - language, fonts, images etc..
#  o Use PyEphem for calculating moon phases, dates for solstice / equinox, etc?
#    - http://rhodesmill.org/pyephem/index.html
#  o Make command-line args more sane
#    - YYYYMM for single month; YYYYMM-YYYYMM for an arbitrary range
#    - or maybe --from YYYYMM / --to YYYYMM for ranges?
#  o Add a debug flag
#    - use for printing font info, it really isn't interesting most of the time
#
# ChangeLog
# =========
import argparse
import itertools
import os
import sys
import reportlab.pdfgen.canvas
from reportlab.pdfgen.canvas import Canvas
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.lib.pagesizes import A4, landscape
from reportlab.platypus import Paragraph, Frame
import calendar
from mx.DateTime import *

#
# Appearance
# - change at will, you need to tweak positioning etc for new fonts
#

# Colors
titlecolor = colors.black
weekdaycolor = colors.black
framefgcolor = colors.black
framebgcolor = colors.lightskyblue
dayboxfgcolor = colors.black
dayboxbgcolor = colors.white

# TrueType Fonts
fonttable = [
    # [ 'Font Specification', 'filename.ttf' ],
    [ 'Bitstream Vera',     'fonts/Bitstream/Vera.ttf' ],
    [ 'Bitstream Vera Bold',   'fonts/Bitstream/VeraBd.ttf' ],
    [ 'Bitstream Vera Italic',   'fonts/Bitstream/VeraIt.ttf' ],
    [ 'Bitstream Vera Bold Italic',   'fonts/Bitstream/VeraBI.ttf' ],
    [ 'Bitstream Vera Mono', 'fonts/Bitstream/VeraMono.ttf' ],
    [ 'Bitstream Vera Mono Bold', 'fonts/Bitstream/VeraMoBd.ttf' ],
    [ 'Bitstream Vera Mono Italic', 'fonts/Bitstream/VeraMoIt.ttf' ],
    [ 'Bitstream Vera Mono Bold Italic', 'fonts/Bitstream/VeraMoBI.ttf' ],
    [ 'Bitstream Vera Serif',   'fonts/Bitstream/VeraSe.ttf' ],
    [ 'Bitstream Vera Serif Bold', 'fonts/Bitstream/VeraSeBd.ttf' ],
    ]

fontmap = [
    # [ 'Font Name', is_bold, is_italic, 'Font Specification' ],
    [ 'Bitstream Vera', 0, 0, 'Bitstream Vera' ],
    [ 'Bitstream Vera', 1, 0, 'Bitstream Vera Bold' ],
    [ 'Bitstream Vera', 0, 1, 'Bitstream Vera Italic' ],
    [ 'Bitstream Vera', 1, 1, 'Bitstream Vera Bold Italic' ],
    [ 'Bitstream Vera Mono', 0, 0, 'Bitstream Vera Mono' ],
    [ 'Bitstream Vera Mono', 1, 0, 'Bitstream Vera Mono Bold' ],
    [ 'Bitstream Vera Mono', 0, 1, 'Bitstream Vera Mono Italic' ],
    [ 'Bitstream Vera Mono', 1, 1, 'Bitstream Vera Mono Bold Italic' ],
    [ 'Bitstream Vera Serif', 0, 0, 'Bitstream Vera Serif' ],
    [ 'Bitstream Vera Serif', 1, 0, 'Bitstream Vera Serif Bold' ],
    ]

# Language
# - will change displayed texts
# - loads special days from "days_[lang_code].txt", eg "days_enUS.txt"
#   for English (American).
#   0 = Swedish
#   1 = English (US)
#   2 = German
#   3 = Catalan
lang = 1

# Page titles
titlefont = 'Bitstream Vera'
titlesize = 44

# Weekday names
dayfont = 'Bitstream Vera'
daysize = 16

# Day numbers
numfont = 'Bitstream Vera'
numsize = 24
numhcorr = 1*mm  # day number position, + = closer to top border of box

# Special items (holidays, name days etc)
itemfont = 'Bitstream Vera'
itemsize = 8
itemwcorr = 1*mm     # item x position, + = more spacing from day number
itemhcorr = -2*mm/3  # item y position, + = closer to top border of box
itemspacing = 2*mm/3 # spacing between item lines, + = closer together


#
# Calendar setup
#

languages = [ 'svSE', 'enUS', 'deDE', 'caES' ]

months = [
    # Swedish
    [ 'Januari', 'Februari', 'Mars', 'April', 'Maj', 'Juni',
      'Juli', 'Augusti', 'September', 'Oktober', 'November', 'December' ],
    # English
    [ 'January', 'February', 'March', 'April', 'May', 'June',
      'July', 'August', 'September', 'October', 'November', 'December' ],
    # German
    [ 'Jänner', 'Februar', 'März', 'April', 'Mai', 'Juni',
      'Juli', 'August', 'September', 'Oktober', 'November', 'Dezember' ],
    # Catalan
    [ 'Gener', 'Febrer', 'Març', 'Abril', 'Maig', 'Juny',
      'Juliol', 'Agost', 'Setembre', 'Octubre', 'Novembre', 'Desembre' ],
    ]

weekdays = [
    # Swedish
    [ 'Måndag', 'Tisdag', 'Onsdag', 'Torsdag', 'Fredag', 'Lördag', 'Söndag' ],
    # English
    [ 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday' ],
    # German
    [ 'Montag', 'Dienstag', 'Mittwoch', 'Donnerstag', 'Freitag', 'Samstag', 'Sonntag' ],
    # Catalan
    [ 'Dilluns', 'Dimarts', 'Dimecres', 'Dijous', 'Divendres', 'Dissabte', 'Diumenge' ],
    ]

# Match colors to codes used in source code and for special days
colortable = [
    {'color': colors.black, 'italic': False, 'bold': False},  # 0
    {'color': colors.red,   'italic': False, 'bold': False},  # 1
    {'color': colors.cyan,  'italic': False, 'bold': False},  # 2
    {'color': colors.black, 'italic': True,  'bold': False},  # 3
    ]

# This table contains dates for special days that can't (?) be calculated.
# Used from the special days data file, like "Tse" instead of "20.3" for date.
day_table = {
    # Spring Equinox
    "se": {
    2005: (20,  3),
    2006: (20,  3),
    2007: (21,  3),
    2008: (20,  3),
    2009: (20,  3),
    2010: (20,  3),
    2011: (20,  3),
    2012: (20,  3),
    2013: (20,  3),
    2014: (20,  3),
    2015: (20,  3),
    2016: (20,  3),
    2017: (20,  3),
    2018: (20,  3),
    },
    # Summer Solstice
    "ss": {
    2005: (21,  6),
    2006: (21,  6),
    2007: (21,  6),
    2008: (21,  6),
    2009: (21,  6),
    2010: (21,  6),
    2011: (21,  6),
    2012: (20,  6),
    2013: (21,  6),
    2014: (21,  6),
    2015: (21,  6),
    2016: (20,  6),
    2017: (21,  6),
    2018: (21,  6),
    },
    # Autumn Equinox
    "ae": {
    2005: (22,  9),
    2006: (23,  9),
    2007: (23,  9),
    2008: (22,  9),
    2009: (22,  9),
    2010: (23,  9),
    2011: (23,  9),
    2012: (22,  9),
    2013: (22,  9),
    2014: (23,  9),
    2015: (23,  9),
    2016: (22,  9),
    2017: (22,  9),
    2018: (23,  9),
    },
    # Winter Solstice
    "ws": {
    2005: (21, 12),
    2006: (22, 12),
    2007: (22, 12),
    2008: (21, 12),
    2009: (21, 12),
    2010: (21, 12),
    2011: (22, 12),
    2012: (21, 12),
    2013: (21, 12),
    2014: (21, 12),
    2015: (22, 12),
    2016: (21, 12),
    2017: (21, 12),
    2018: (21, 12),
    },
    }

# ----------------------------------------------------------------------------

# loadDays()
#
# Load special days from data file.
#
# funs   Call table mapping letters to functions we want to call.
#         Example: for loadDays({"E":easter}), if we find a line
#                  like "E-10 Some Holiday", we would make the
#                  following call: easter("-10")
#
def loadDays(funs):
    import codecs
    fname = 'days_' + languages[lang] + '.txt'
    res = []

    try:
        f = codecs.open( fname, 'r', 'utf-8' )
    except IOError:
        print "Warning: Unable to open " + fname + ", skipping."
        return res
    
    
    for line in f.readlines():
        # format: month.day color_code:Text..
        line = line.strip(' \t\n\r')
        if line[0] == '#':
            continue
        day = line.split()

        if len(day[0].split('.')) > 1:
            date = day[0].split('.')
        else: # go to call table
            date = funs[day[0][0]](day[0][1:])
            
        what = ' '.join(day[1:])

        for part in what.split('/'):
            part = part.strip()
            style = 0
            
            if len(part.split(':')) > 1:
                style,part = part.split(':')

            res.append([(int(date[1]),int(date[0])),
                        int(style), part.encode('utf-8')])

    return res
    

# drawHeader()
#
# Draw the calendar page header.
#
def drawHeader(c, year, month, width, height):
    c.saveState()

    c.setFillColor(titlecolor)
    c.setFont(titlefont, titlesize)
    c.drawString(0, 0, months[lang][month-1])
    year_width = c.stringWidth(str(year), titlefont, titlesize)
    c.drawString(width - (year_width+15), 0, str(year))

    c.restoreState()
    

# drawGrid()
#
# Draw the calendar grid and all its contents.
#
def drawGrid(c, year, month, width, height):
    # return date for easter + diff, negative = before easter
    def easter(diff):
        d = Feasts.EasterSunday(year) + RelativeDateTime(days=int(diff))
        return d.tuple()[2], d.tuple()[1]
    # fetch date from per-year table, for specified code
    #   se = spring equinox, ss = summer solstice,
    #   ae = autumn equinox, ws = winter solstice
    def table(what):
        return day_table[what][year]
    
    reddays = loadDays({
        "E": easter,
        "T": table,
        })
    gridspace = 2*mm

    # set up special day item styles
    styles = []
    for col in colortable:
        style = ParagraphStyle('normal')
        style.fontName = itemfont
        style.fontSize = itemsize
        style.textColor = col['color']
        styles.append(style)
    
    c.saveState()

    grid_h = (height - daysize - 5*mm) / 6
    grid_w = width / 7
    box_h = grid_h - 3*mm
    box_w = grid_w - 3*mm

    # calculate longest day string
    num_w = 0
    for n in range(31):
        nw = c.stringWidth(str(n+1), numfont, numsize)
        if nw > num_w:
            num_w = nw
            
    # week names
    c.saveState()
    c.setFillColor(weekdaycolor)
    c.setFont(dayfont, daysize)
    for day in range(7):
        c.drawString(0 + day * grid_w, height - daysize, weekdays[lang][day])
    c.restoreState()

    # day grid, set 0,0 = lower left corner of upper left grid position
    c.translate(0, height - grid_h - daysize - 5*mm)

    pos = 0
    for week in calendar.monthcalendar(year, month):
        for day in week:
            if day > 0:
                isred = False
                
                # calculate lower left corner for this day
                x = pos % 7 * grid_w
                y = 0 - pos / 7 * grid_h

                # paint a rounded rectangle
		c.saveState()
                c.setStrokeColor(dayboxfgcolor)
                c.setFillColor(dayboxbgcolor)
                c.roundRect(x, y, grid_w - gridspace, grid_h - gridspace, gridspace, fill=1)
		c.restoreState()

                # handle special days
                items = []
                for rd in reddays:
                    if (month, day) == rd[0]:
                        if rd[1] == 1:
                            isred = True
                        txt = rd[2]
                        if colortable[rd[1]]['italic']:
                            txt = '<i>' + txt + '</i>'
                        if colortable[rd[1]]['bold']:
                            txt = "<b>" + txt + "</b>"
                        items.append(Paragraph(txt, styles[rd[1]]))
                if len(items) > 0:
                    fx = x + num_w + itemwcorr
                    fy = y
                    fw = (x + box_w) - fx - 1*mm
                    fh = box_h + itemhcorr
                    f = Frame(fx, fy, fw, fh, leftPadding=0, rightPadding=0,
                              topPadding=0, bottomPadding=0, showBoundary=0)
                    f.addFromList(items, c)
                    
                # set color if red day
                if isred or calendar.weekday(year, month, day) == 6:
                    c.setFillColor(colortable[1]['color'])
                else:
                    c.setFillColor(colortable[0]['color'])

                # draw the day number
                c.setFont(numfont, numsize)
                c.drawRightString(x + num_w + 1*mm, y + box_h - numsize +
                                  numhcorr, str(day))
            pos = pos + 1
    c.restoreState()


# drawCoverPage()
#
# Draw the cover page.
#
def drawCoverPage(c, filename):
    width = landscape(A4)[0] - 20*mm
    height = landscape(A4)[1] - 20*mm

    # leave 1cm margin on page
    drawable_h = height - titlesize - 5*mm

    # draw image
    c.drawImage(filename, 10*mm, 10*mm, width=width, height=height,
                preserveAspectRatio=True)

    # show the page
    c.showPage()

    
# drawCalendarPage()
#
# Draw the entire calendar page.
#
def drawCalendarPage(c, year, month):
    width = landscape(A4)[0] - 20*mm
    height = landscape(A4)[1] - 20*mm

    # leave 1cm margin on page
    drawable_h = height - titlesize - 5*mm
    c.translate(10*mm, 10*mm)
    
    # draw rounded background rect
    c.saveState()
    c.setStrokeColor(framefgcolor)
    c.setFillColor(framebgcolor)
    c.roundRect(0, 0, width, drawable_h, 5*mm, fill=1)
    c.restoreState()

    # place header 5mm from the left/right border sides
    c.saveState()
    c.translate(5*mm, height - titlesize) 
    drawHeader(c, year, month, width - 10*mm, titlesize)
    c.restoreState()

    # draw grid with a 5mm margin to the border
    c.saveState()
    c.translate(5*mm, 5*mm)
    drawGrid(c, year, month, width - 10*mm, drawable_h - 10*mm)
    c.restoreState()

    # show the page
    c.showPage()
    return


def drawMonth(c, year, month, image_files):
    try:
        image_file = next(image_files)
        drawCoverPage(c, image_file)
    except StopIteration:
        pass
    drawCalendarPage(c, year, month)

def run(args):

    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.lib.fonts import addMapping

    # Process args
    parser = argparse.ArgumentParser(
      formatter_class=argparse.RawDescriptionHelpFormatter,
      description='Generate calendar pages in PDF format.',
      epilog='''PyCalendarGen 0.9.4, Copyright (C) 2005-2012 Johan Wärlander
PyCalendarGen comes with ABSOLUTELY NO WARRANTY. This is free software,
and you are welcome to redistribute it under certain conditions. See the 
file COPYING for details.''')
    parser.add_argument('year', type=str, metavar='YYYY',
                        help='The 4-digit starting year for the calendar '
                             'page, like 2012.')
    parser.add_argument('month', type=str, metavar='MM[-NN]',
                        help='The number of the month you want to generate '
                             'a page for, like 05 for May. If of the format '
                             'MM-NN, it describes a range of up to 12 months. '
                             'In this case, if NN < MM, it means the calendar '
                             'wraps into month NN of the next year.')
    parser.add_argument('filename', type=str, nargs='?',
                        help='The name of the PDF file to be written. By '
                             'default, it will be named like YYYY-MM.pdf.')
    parser.add_argument('--cover-image', type=str, metavar='FILENAME', nargs='?',
                        help='Generate a cover page using the specified image.')
    parser.add_argument('--monthly-image-dir', type=str, metavar='DIRECTORY', nargs='?',
                        help='Generate an opposing page for each month, with '
                             'an image taken by cycling through the files of '
                             'the specified directory in alphabetical order.')

    args = parser.parse_args()

    # Load fonts 
    for spec in fonttable:
        pdfmetrics.registerFont(TTFont(spec[0], spec[1]))
    for font in fontmap:
        try:
          addMapping(font[0], font[1], font[2], font[3])
          print font
          print "added."
        except Exception, e:
          print "Error adding Font:"
          print e
        
    # Font test page
    if 0:
        c = Canvas("fonts.pdf", pagesize=portrait(A4))
        ypos = 100
        for font in fonttable:
            c.setFont(font[0], 24)
            c.drawString(100, ypos, font[0])
            ypos += 24
            c.save()
        
    # Handle filename
    if args.filename is not None:
        fname = args.filename
    else:
        fname = args.year + '-' + args.month + '.pdf'

    #    
    # Draw the calendar
    #

    # Initialize PDF output
    c = Canvas(fname, pagesize=landscape(A4))
    c.setCreator("PyCalendarGen 0.9.4 - bitbucket.org/jwarlander/pycalendargen")
    year = int(args.year)
    month = args.month

    # Draw cover page
    if args.cover_image is not None:
      drawCoverPage(c, args.cover_image)

    # Set up iterator for monthly images
    image_files = []
    if args.monthly_image_dir is not None:
      print args.monthly_image_dir
      image_dir = args.monthly_image_dir
      image_files = [os.path.join(image_dir, f) for f in os.listdir(image_dir) 
                     if os.path.isfile(os.path.join(image_dir, f))]
      print image_files
    image_files = itertools.cycle(image_files)

    # Draw monthly page(s)
    if len(month.split('-')) > 1:
        start = int(month.split('-')[0])
        end = int(month.split('-')[1])
        if end < start:
            for m in range(12-start+1):
                drawMonth(c, year, start+m, image_files)
            for m in range(end):
                drawMonth(c, year+1, 1+m, image_files)
        else:
            for m in range(end-start+1):
                drawMonth(c, year, start+m, image_files)
    else:
        month = int(month)
        drawMonth(c, year, month, image_files)
            
    c.save()


if __name__ == '__main__':
    run(sys.argv)
