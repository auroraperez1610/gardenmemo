from flask import Flask, render_template, request, jsonify, send_file
import json, os, base64, io, uuid, tempfile
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.platypus import (BaseDocTemplate, PageTemplate, Frame,
    Paragraph, Spacer, Table, TableStyle, Image as RLImage,
    PageBreak, HRFlowable)
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.graphics.shapes import Drawing, Circle
from PIL import Image as PILImage
 
import os as _os
app = Flask(__name__, template_folder=_os.path.join(_os.path.dirname(__file__), 'templates'))
app.config['MAX_CONTENT_LENGTH'] = 32 * 1024 * 1024
 
DATA_FILE = 'catalog.json'
 
VERDE_OSC  = colors.HexColor('#2D5016')
VERDE_MED  = colors.HexColor('#4A7C28')
VERDE_CLAR = colors.HexColor('#7DB544')
BEIGE      = colors.HexColor('#F5F0E8')
GRIS_MED   = colors.HexColor('#666666')
BLANCO     = colors.white
PAGE_W, PAGE_H = A4
 
LOGO_B64 = "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07NLhSAmBhYoBMrjvYd7QXbkVicASI8NOTmgGDq2dDJpFalNmw82AASz2eFBE2vOXAtoapF3/IuYTX1/g0Xs7eZeGfnfOYhACM7LYdaZYkPIJKXtbN7EACjEodymTlQUYq8s6JWR//zBAACB4kJgnZFnGtiyvO7OHW5zMyDCsVmvvheRX2BIWqV9OJ0ZywCITOS1dW1dYusWAOBeRPYi8v9WRIIs78NCdhBEjIwsgJPJ5McfGyelt6N67cj/M98GAcBbWmYFgqyN4maNaBGBJWKrVzFztinZe/TKyP8Ld9suLaNwDur0psTIQMzC40999nmqZh8gEuverupF5P8dIq28XFlaSto9sFDNDB5L1jXGVq4CAKZexd2LyENZfvy/vFkbE4FleftXaNeFg+PSGFX7kqWQVY/l6Pq0f749/5t2pPk8ROw2fI/Mnn4HpSR3c705KbozpHq4vltzrYfLzHNEj+YaMxOREAe23TQFbaXsaUXE7Glsnqy17v5iZgFgD64S3Bmp6A8kP/7YaWy0CwrSW8n9d1Bluu6w4ZNElH2l+dIeOqTnkT3UK47w+uy3I+JhG9NtV3cjIzNjfKhGdP1X1+t7AEr287OxZU52Pbp9V+aQUgoheiiZrLVGRCklIhJpx0kZLEopiehQW2kbBAshTAsNHLuZMAgA4B08VFsepIN23JaWDfv3ti1fikemuDPdkvmuTv3T9XqtdeZK13WVcs2Xmg7peu+hev4welMc0Qa6mX42g0504E8zbXp+Raaru5GRjuN8//vf371790MPPTR06FAzNh10B7que9ttt23btu2Xv/zlqFGjlFKWZb322muPPPLIDTfccMUVV7iua9v2tm3bbrvttrKysocfftjn82UKgJhJs3379ttuu62wsPB3v/tdKBQCANd1vve979XX13u93kzLpLRaWlq+/e1vX3DBBUZKKaV+8IMf7Ny50+/3ak0ejz1y5KhLLrlk0KBBWe08CFhSyoaGhueff/7999/fvXun1iocjowdO27GjJlTp07NgK/TyAkhtmzZ8tBDv169enUgEJgxY+Z3v/td27Y7VzJhBABfVRXk5XIsBlIeoHsQWUD72/MKz7/wsNaQeewvf/nLpUuXhkIhRBw6dOiNN95YXl7ebe0Uc1JKuX79updeemn58uUNDfUAUFRUdPLJp1xyyVdHjBieuSx7jn3wwQcPPPDA+eeff8stt3TbY51eQUTf/va3zjxz6uWXX97D9WZ0otHoCy+8sHDhe9u2bVNKFRQUTZ48eebMmePHj+/UmE4z/7e//W1jY+PPfvazbq5RSjHzt771TQC4//77mNmcYWalNDMvW7YUAKqqqlpaWpjZcRxm/vWvfwUA99xzd+ZMPB4fNWoUACxYsODghyhmfuihhwDgqquuypxJJBIVFf3g4KgDyxIA8NBDD2Ye6zjOmDGjASC7Z8rKSp599i/ZbzH6QimXmZ977q9Dhw42VwaD/kgkZNsSALxe+6qrrti3b58RNtk3EtHOnTuGDRsMAKFQwFx/yy3fI6LsK83Fmkg77ubLL918wrAtk8ZvmTA2/TNx/Nbxoz8/aXJ8125m1qSI+FCHeezMmTMBwO6o0jt+/Nj9+/d1+1IinUjE77rrx4WFeebicDgYiYTM78XFRffff6/jpMy3ZPf8888/DwDXXntNp+46VJNWr/4EAM4660wiTYf4APOc1157xQwNAPh8nmDQb37PzY3ceusttbU12Y3JfAgztbdHBw+uys3Nqa6u7jh54EgjctmyZYGAf9KkiYlEMnOR+dePfvQDALjvvnvNGXPyD394WEr5858/wMyu62bD7uabb87+eCJyHOe0007zeOx3332XmQ1uksnkiBHDSkqK/vGP599779133pn/7rvvvPfeu2++OXfnzh2ZDnJd95RTTs7NjTz11JPvvPP2iy++cNNNN3i9diDg63jaQdB/+OHfSolS4qxZM1566cUNG9Zt2bL5gw8WP/DA/QMHDgCACRPG79mzJxuU5sZbb70ZAC6//LL169fNm/dm377lALBs2dKuA0mO0sz77rt305BBWydPyCBy64Sxm08c/+nQIbVPPMXM7LrEh8SkefvVV3/NsuSDD/5izpzZs2bNAICf/OTurjNNa51Kpa688nIAyMvLueWWm+fPn7dp02ebNn321ltvfuc73zLQvP7665RSWuvs4Xv55ZeklN/+9rcOi0jz37vuutO2rZKSonXr1nWautktf/LJJ30+GwDOPnvqn//8zMqVH61fv27+/Hm33fb90tJiADjzzC/F4/FOaDOvmDt3Tjgc9Pu9Tz75hBnigxBpcOw4qZNPnuLx2AsXLjR3mmdFo20nnDAiGPR//PGqbET+/ve/A4Cf/eyn5ommlZ9+ujEnJzJo0KDGxsYOoaWYefny5T6fb+zY0bFYOzMTaYPIoUMHl5YWNzc3dttBpgGu606ZMiUSCe3evTvzrwceuB8ATj/9tGQyaS7TWjHznDmzfT5vOBx89NH/7PrAbdu2Tpv2ZQA477zz4vF4pq/NE8444zTbttatW29O/u1vzz722B+bmho7TXRiJtdh5rrXXv1s2KCtk7Nk5IQxmyeP33rC8E2XzHKTMeoqIrqM69e+dhUArFixjJkXL34fAGbMuLATDkwf3nnnHQAwdOjgRYve7/q0t9+eP2jQQAC4//77M7ebG1966UUA+OY3b+oZkaal8Xh8/PixOTlhyxLmUZ1uMX8uWrQoHA77/d5f/OJnrut0etTatWsvvviit956s6uwN39+/etfNzLlggu+0rWTIPOaX/7ylwBwyy03ZyNvzpw3pJRnnTW108zrhEjzMiKaPn06ALz44gvZsvNHP/ohANx9993ZWDeILCkp2rVrh+u6qVTK7ThMuzshcsOGDUqpZDKptU4mE2PHjvb5PKtXf5J5ZjQanTBhHCI89NBDpj3mUVprpZSxAWpra8eNGwsATz75eOZbzOumT58uBD7++GOZOdODemPmxPZtG04av238mM0Tx26ZMOaApJw0bsMJIxrfX8DMdGgEmJdeddWViPib3/x6wYIFl156cV5e3t/+9pxpcPZlq1atjERChYUFS5Z8YCwZIwvNlQYT7733Xl5ebn5+7vr1a82N/y1Emn/Nnz/P7/f27983HA5OmjQhmUwYk6EDtUxEiUT89NNPBYC7777LDFN2Px8W9DU11RUV/QoK8srKSgoK8jZuXN9pBorM4tj06dNzciJvvjm3qalJSmm8jVdffVVrPXPmLONAHdZUnzVrFgC88sorxp8yxu/cuXOCQf+MGTOgu+RQ27Yty/J4PFbH0a01bZxl27YBwOv1VVVVJZOOse6N0/f++++vXr32tNNOvfXWW80Z8yjTDNu2XdctLi6+8847hcDnnnuOSJsXmS+95pprmeHOO+/41a9+UV9fn/Ftu3MUEQA8/fsF+g+ilAOdnCQUtnKjr75KB5fwO5SDb9virrvumjp16ssvvzxw4ID+/ftnu7qmbc8//3xbW/sNN3z9lFNONX6kcWnNp1mW7bru1KlTr7322qamlhdeeOF/zA6+/vqriUTqpptuOumkk9asWfvRRysAMDPuzISIy5cv+/DDZePHj73jjjsMyLL7OUNodEWLOfP222/v2rXnggsuuPzyyxsbm+fOnduptcJAh4iGDx9+2mmnbt26fcGCBQBgWVZ1dfX8+W8XFuaff/75cLhMYzO606ZN69OnfMGC93bt2mXOLFq06NNPP58yZcqYMWO6c764rS0aj8fb29vj8Xg8Ho9Go6lUqtvBy5gBWuu9e/d4PFZubl7mgqVLlxLRhRdeaFlWt16eOX/22WdXVg7YuHHjrl27jGtpOvGSSy6+775729vbb7/9xyeeeOKPf/xjMzO7m4cIWgtp2+PGaeVIEAdF2mqyAv74imWJbZtRCOhxGiOi1jx+/Php0748aNCgTz5ZPW3atKeffjpDoBi2YeXKlbZtzZo161B0r2FSZsyYYVnyww8/PCzz2lWaSCkbGxvmzZsfCgW//vWvT5s2zXXVa6+91hVSS5cuVUpPnz7d7w902x4zo7qeNwyUeeasWbOuvPJKRHzjjTdc181mgkQ2KTpr1kUA8OqrL5tWzp//1t69+6ZOPbuysrJn4sC8j4jKy8unTTuntrb+zTfndEjZV4ho5sxZlmWZt2T3QiKRnD79gvHjx06YMH7cuLGTJk0YNKjqb397zpAA2c8PBAJCCI/HI6V88snHP/549ejRY4YPH5HplD17dgPAkCFDeqg8i4iRSKSqqqqhoTEjCDMjevfd97z77oJrr722tbX1F7/4xXnnnbt165ZulYPJXQhOGgfS4s7cI5MtRVNb05y5eLiCkEIIrenee++bN+/t999ffOeddxLRLbfcvGTJksx729vbq6v3FxYW9OnT71DEtTk/YMCAnJxwdXV1IhH/b4lJowrefffd7dt3nnfeuWVlfWbMmJGXlzt37tzW1taMwjRRxvv27QOA4cOHd/t8Ywp2sPe6E+mzdeuWhQsXDBo08Mtf/vLEiZOnTJm8cuXKVatWGvAchEgzqOeee255eem77767c+dORHz55ZcB4KKLZh3h55lrZs2aJQS++uoriFhdXT1//rzCwvzzz/9Kt1LWWNOxWCwWa4/F2mOxWDQaVcrt+vANGzZ8/vlnH3yw+M4777j99tsB+Pbb7wgGgxmUd/TaYRcbur/AGDonn3zKn/70pwULFk6ffv7KlatuuOHr7e3tXT/fjE1g5AlUXAKu05nS12D57cS8eU5bGwpxhPFpZWVlP/3pA1dffXUsFn/mmWeyXnqkiy5C4P8sL8KM/ksvveTx2DU1NTfe+I0HHnggLy9327bt77zzbkY6mvdn5nDXbjFjsWHDunHjxn7ve98xm7JlY+P1119vaWn1+Xy33nrrTTd9w3VdpbSBWedVRDMjy8v7nHPOOX/6018WLXrf6522aNHiqqoBZ5119qEWfLr9sNNPP2PYsKFLlny4e/fuFStW7NtX/dWvXlJZWdVJyiKi1trv97/22ut9+vQ1lp85mZuba5Rsh3kKWuvLLruUiDweTzKZlFI+8MADF198sdG5Zor36dMHALZu3drD/GHm9vbojh3b8/NzCwoKsidJx8IDMfPYsWOff/7v06dPX7jw/RdffPH666/vvKiICEx2SR/v8BHuovekxwP6wBsJWHg9tHNn2/vvFV44i4nwcDrU+Cu2bX/jG9945pmnN2/erJSyLAkAwWCotLR0xYqPqqurDX9+iOnEu3btbmuLjho1yu8PABxpsSszLtu2bV+yZInXay9ZsvSDD5YaihERXn31lUsuuTiz2CGEKC0tNf18qEkSi8XXrFmbn5+X3gjKZBVLqZR64403vF7P5s2bN2z41NDPXq9n3rx5d9/9k5ycSHqFqauEQ8S5c+f+9a9/iUbbp007r7Cw0MDlCCJjUGsdieR85SvnJxLJv/71z7Nnvw4AF1108aFQIoTs37+irKysb9++ffr0KS8v79evXzgc7nrl6NGjJ0+e7PP5vF7fH/7whx/96A6lVDbETzrpZEScM2cOs+520UwphYiLFi3avn3n8OEjKyoGZA/bjh3blHKNee66TjAYuummGxFxxYplhwq5EADBsWNJd9mzlkEQCCmbZ79B2mxKwoftOmN+5ebmWpaVSMQdxwFApZRt2xMmTHRdNXv269na7eC2KCFwzpzZrqtOOunkjCI+QkQCwJtvzqmpqf3yl6e9/vrrr7326uzZsx9//Mni4tIFC97du3ePEVimr048cYqUYu7cua6bMnOhq2CSUphZYXrGNObjjz9etWrV4MFDnn/+77Nnv/HGG6+//PIrEyZM3LRpk2G+0ovdnSTcGWecOXTo4AUL3vvjH//o83lnzpz1P9ACM2fODAb9jz/++Pz58ysrK3qQssyQTCYNO6M6juxOR0RmkFI+/fTTixZ9cNlll0ej7StXrso2Fs2Tp04964QTRi5c+P5jjz1mBGeGsTIMhW3bra2tP//5z5TSl112mWVZBqPxeOzii2edddZZLS0t5i7jYEYiOQDguqpbeWPO+MaNQY9fdEGJQrJ9PvfjtbGN60Ag9bjMnXHaEHHNmjXJpFNQUOj3+zPfePnlVwQC/scff/yTT1YZ0oCyDtd1bNu7fPmHzzzzTCQSvuSSS7s2OLM0lTmyVm6l1vr1118TAr/5zW9Nn37hjBkzL7jggquvvnrq1Kk1NXVvvvlWRkAy82mnnT5u3LgPP1z2n//5n1JanfpZaw3A3a5rv/76a4lEcubMWRdddPEFF0yfPv3CCy+cceWVX1NKv/baq5k2d1ajOTk55513XltbW2Njw4gRw0899dQjVNnZTt+kSZPHjBnT3Nzc3Nwybdq0wsLCbJ+m08iGQqEjYX9MU++66+7hw4c+/vgT//jHCxl93dHyyD333COlvPPOO5999lnLsgxFYsSPbdu1tbXXXXfdsmUrvvSl06+77jrjWjGzx+PZu3fvrl2733nnnQzHJIR46aWXmHnIkMGHCLkQAOAbPARKi8l1IUvbIAAzaAusWLT1jdlwOAnp9/uFEH6/v66u7sEHH2TmCy+cns0DTJky5aabbqypqbv++utXrVplmpc5bNu7fPmyG264ob6+8Tvf+fb48eNNQMbBPINtOqFTOIsZlzVr1ixfvmLEiBEnnXSSYRUdx9FaX3TRRULga6+9alpimhQMBu+55x6Px3Pvvfc+88xTlmVn+tn0ueuq7FAY08/RaHTOnDnBoP/CCy80VLFhMc8779zi4qL589/ev39/2pnrSpMuXrw4Ly/X67UNBdota/+HPzwshMisIna94Oc/f8Dn80Qi4bfffrvrsljWKmLxO++8vWHD+jVrPlm7ds26dWs/+WRVXV1NFkPunHzylNzcyGeffWZu/8c//mFZ1tChg2tqqrPJVfPLAw/8FAC8Xs8111w9f/687du37d27Z8OG9Y888h8nnDASAEaMGL5ly5ZOCxsvvPC8EFhVVfnii//Ys2f31q1b7rzzDtuWFRX9du3a2XXt1SzemIWiHd/7zpYRQ7dMmbB10rgtkw/8bD5x/JYJJ2w+a2qyoUF38OpdVxGllI8//tjGjRvefHPuGWecDgCnnXZKe3s0I8mM4Glvb585c4ZZ07/zzjtWrFi+Z8/u3bt3LV++7Pbbf1hcXAAAX/3qpYlEotNaxksvvWhZ8vLLv7px44bVq00nr1mzZnU02sbMrquY+d57fwIAt9/+o8xd5gktLS3Dhg3JzY1s3LihU489+OCvEMHjsa688vI335y7ffu2/fv3btr0+dNPP3niiZMB4OKLL84m6ufNe8u27alTv5RZIsk88Morr0AUf/rTM+bh0JVYTyaTkyZNBIDVq9d0XdnsWMJ+EADuvfeerog013/22UbbFqNGnZBIJDqNqPk9kUhUVlZIibYtzUq0lOD12gDw298+xMyO4zKz66bGjh1tWWLjxo2Zd1122VcB4Morr8hexs207Y9//GO/fn3NBC0szO/btywQ8JlYjRkzpm/evLnTR2mtiOjmm79rbikvL83PzwWAnJzwa6+92u3abvpGpZh5/zNPbKjos3X08M0jh2waOTT7Z8voERv796t++klmZld17SXDY/h8HhNiAgATJ07YvHlTtz0WjUZvueWWUCgAALYtyspKSkuLpUQAiETCt932/Xg8nn2j6Y1nn30WAPx+r5QoBEiJ5l0LFy4wF7e2tgwZMggRli9f1jVO4N/+7VYAuOuuO7r+66mnnqyo6G+anZ+f27dveTgcNF7fFVdcsXPnTjOXzABdddUVAPD73/8u+zlmNF988QUAmDr1S0q5RGR1tWm8Xu/XvnbVwIGVo0eP6kqBGmlfXl4+duzYvn37djVZjOIeNmzEZZddPmrUKJ/P1230qxA4fvz4vn37HhyNJpubm/v1OygmaMyYMZFIxO/3Z+697777Ghsbtm/f8cknqydNmpgxCYyO++Y3v3nuudP++te/LF68eN++fa7rjhxZPnz4yEsuucQscnb1+gH497//w/jxE5577tk9e/YUFBR85StfufXWWydOnNwDEWv8wpxTT20/9TSbhe5yFQsRiEfdXbsUOVJ6ulotQ4cOPfHESTk5OUopr9c7ZcrJ3/ve9/Lz87u2kJlDodDvf//7q6664rnnnv3kk9X19fWIOGjQoEmTJn/ta1d3DQAzvxQVFU2ZcmIoFMw2PJRShtBAxC1btkQikWuuST8h817z0ssvv3zJkiX799e4rmvYj0w/f/3rN5x99pefffbZxYsX7t27z3GcsrKyUaNGXXHF5WefPS278S0tLdFo9PTTT73ggguyX2FQceaZXzr//PPi8VhNTU2fPn0PE8jZA9tseJlDEWD/3AZp2WU/uYdXGFe029A983s02qY1+f0+r9fXY5R7pgoKtLa2WJYdDAZNFOrhCi2bTWQ7aq502dcLEIi0QITDFLE48JmHmgNGpJlPM3ocAMLhkGnhkQd+d3qjMTp7vpFIA3Rehjm4n6NE2ufze73ero0hIsTDlPHIDA0eit/65zfcS4/R/w85J6Yqc48bWxMRGz7vyLMasru4h7D7nqbPP/dRnTIxDtFIAuDsDzHcnPjnsnIPlYXRMxKMsSullbmk534+klyP/w9t3Kx4XiyFegAAAABJRU5ErkJggg=="
 
def load_catalog():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE) as f:
            return json.load(f)
    return []
 
def save_catalog(data):
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
 
@app.route('/')
def index():
    return render_template('index.html')
 
@app.route('/api/catalog', methods=['GET'])
def get_catalog():
    return jsonify(load_catalog())
 
@app.route('/api/catalog', methods=['POST'])
def add_species():
    data = request.json
    catalog = load_catalog()
    species = {
        'id':      str(uuid.uuid4())[:8],
        'name':    data.get('name', ''),
        'notes':   data.get('notes', ''),
        'icon':    data.get('icon', None),
        'photo':   data.get('photo', None),
        'created': datetime.now().isoformat()
    }
    catalog.append(species)
    save_catalog(catalog)
    return jsonify({'ok': True, 'species': species})
 
@app.route('/api/catalog/<sid>', methods=['DELETE'])
def delete_species(sid):
    catalog = [s for s in load_catalog() if s['id'] != sid]
    save_catalog(catalog)
    return jsonify({'ok': True})
 
@app.route('/api/catalog/<sid>', methods=['PUT'])
def update_species(sid):
    data = request.json
    catalog = load_catalog()
    for s in catalog:
        if s['id'] == sid:
            s.update({k: data[k] for k in data if k != 'id'})
    save_catalog(catalog)
    return jsonify({'ok': True})
 
@app.route('/api/generate', methods=['POST'])
def generate_pdf():
    data         = request.json
    project_name = data.get('project_name', 'Proyecto')
    address      = data.get('address', '')
    plan_b64     = data.get('plan_image', None)
    species_list = data.get('species', [])
    buf = io.BytesIO()
    _build_pdf(buf, project_name, address, plan_b64, species_list)
    buf.seek(0)
    filename = f"Memoria_{project_name.replace(' ','_')}.pdf"
    return send_file(buf, mimetype='application/pdf',
                     as_attachment=True, download_name=filename)
 
def b64_to_img(b64str):
    if not b64str:
        return None
    header, data = b64str.split(',', 1) if ',' in b64str else ('', b64str)
    raw  = base64.b64decode(data)
    path = f'/tmp/{uuid.uuid4().hex}.jpg'
    with open(path, 'wb') as f:
        f.write(raw)
    try:
        pil = PILImage.open(path)
        if pil.mode in ('RGBA', 'LA', 'P'):
            bg = PILImage.new('RGBA', pil.size, (255,255,255,255))
            src = pil.convert('RGBA')
            bg.paste(src, mask=src.split()[3])
            pil = bg.convert('RGB')
        else:
            pil = pil.convert('RGB')
        out = path.replace('.jpg', '_n.jpg')
        pil.save(out, 'JPEG', quality=90)
        return out
    except:
        return path
 
def rli(b64str, max_w, max_h):
    path = b64_to_img(b64str)
    if not path or not os.path.exists(path):
        return None
    pil = PILImage.open(path)
    w, h = pil.size
    ratio = min(max_w / w, max_h / h)
    return RLImage(path, width=w*ratio, height=h*ratio)
 
def dot_drawing(w, h):
    d = Drawing(w, h)
    r = min(w, h) * 0.38
    c = Circle(w/2, h/2, r)
    c.fillColor   = VERDE_CLAR
    c.strokeColor = VERDE_MED
    c.strokeWidth = 1.5
    d.add(c)
    return d
 
def get_logo_path():
    """Decodifica el logo base64 a un archivo temporal y devuelve la ruta."""
    raw = base64.b64decode(LOGO_B64)
    path = '/tmp/logo_bolaga.png'
    if not os.path.exists(path):
        with open(path, 'wb') as f:
            f.write(raw)
    return path
 
def header_footer(canvas, doc, project_name, address):
    canvas.saveState()
    # Fondo verde cabecera
    canvas.setFillColor(VERDE_OSC)
    canvas.rect(0, PAGE_H-1.8*cm, PAGE_W, 1.8*cm, fill=1, stroke=0)
 
    # Izquierda: nombre del proyecto (grande) + dirección (pequeña debajo)
    canvas.setFillColor(BLANCO)
    canvas.setFont('Helvetica-Bold', 11)
    canvas.drawString(1.5*cm, PAGE_H-1.05*cm, project_name.upper())
    if address:
        canvas.setFont('Helvetica', 8)
        canvas.setFillColor(colors.HexColor('#C8E6A0'))
        canvas.drawString(1.5*cm, PAGE_H-1.55*cm, address)
 
    # Derecha: logo
    try:
        logo_path = get_logo_path()
        pil = PILImage.open(logo_path)
        lw, lh = pil.size
        max_h = 1.3*cm
        max_w = 4.0*cm
        ratio = min(max_w/lw, max_h/lh)
        draw_w = lw * ratio
        draw_h = lh * ratio
        x = PAGE_W - 1.5*cm - draw_w
        y = PAGE_H - 1.8*cm + (1.8*cm - draw_h) / 2
        canvas.drawImage(logo_path, x, y, width=draw_w, height=draw_h,
                         preserveAspectRatio=True, mask='auto')
    except:
        pass
 
    # Línea verde clara bajo cabecera
    canvas.setStrokeColor(VERDE_CLAR)
    canvas.setLineWidth(1.5)
    canvas.line(0, PAGE_H-1.82*cm, PAGE_W, PAGE_H-1.82*cm)
 
    # Pie beige
    canvas.setFillColor(BEIGE)
    canvas.rect(0, 0, PAGE_W, 1.0*cm, fill=1, stroke=0)
    canvas.setFillColor(GRIS_MED)
    canvas.setFont('Helvetica', 7)
    canvas.drawCentredString(PAGE_W/2, 0.38*cm, f'Página {doc.page}')
    canvas.restoreState()
 
def _build_pdf(buf, project_name, address, plan_b64, species_list):
    frame = Frame(1.5*cm, 1.2*cm, PAGE_W-3*cm, PAGE_H-3.2*cm,
                  leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
    pt = PageTemplate(id='p', frames=[frame],
                      onPage=lambda c, d: header_footer(c, d, project_name, address))
    doc = BaseDocTemplate(buf, pagesize=A4, pageTemplates=[pt])
 
    dist_st = ParagraphStyle('dist', fontSize=11, fontName='Helvetica-Bold',
                              textColor=VERDE_OSC, spaceAfter=6, spaceBefore=4)
    sec_st  = ParagraphStyle('sec', fontSize=9, fontName='Helvetica-Bold',
                              textColor=VERDE_OSC, spaceAfter=5)
    fic_st  = ParagraphStyle('fic', fontSize=18, leading=22, textColor=VERDE_OSC,
                              fontName='Helvetica-Bold', spaceAfter=2)
    ley_st  = ParagraphStyle('ley', fontSize=6.5, leading=8, textColor=BLANCO,
                              fontName='Helvetica-Bold', alignment=TA_CENTER)
    cnom_st = ParagraphStyle('cn', fontSize=9, leading=12, textColor=BLANCO,
                              fontName='Helvetica-Bold', alignment=TA_CENTER)
    cnot_st = ParagraphStyle('cno', fontSize=7.5, leading=10, textColor=GRIS_MED,
                              fontName='Helvetica', alignment=TA_CENTER)
 
    story = []
 
    # PÁG 1 — Plano + Leyenda
    story.append(Paragraph('Distribución de especies', dist_st))
    story.append(HRFlowable(width='100%', thickness=2, color=VERDE_CLAR, spaceAfter=8))
 
    if plan_b64:
        plano = rli(plan_b64, PAGE_W-3*cm, 13*cm)
        if plano:
            story.append(plano)
    story.append(Spacer(1, 10))
 
    if species_list:
        story.append(Paragraph('LEYENDA DE ESPECIES', sec_st))
        N  = len(species_list)
        IW = (PAGE_W-3*cm) / N
        IH = 2.5*cm
 
        icon_cells, name_cells = [], []
        for sp in species_list:
            img = rli(sp.get('icon'), IW-8, IH-8) if sp.get('icon') else None
            if img:
                cell = Table([[img]], colWidths=[IW])
            else:
                cell = Table([[dot_drawing(IW*0.7, IH*0.7)]], colWidths=[IW])
            cell.setStyle(TableStyle([
                ('ALIGN',(0,0),(-1,-1),'CENTER'),('VALIGN',(0,0),(-1,-1),'MIDDLE'),
                ('TOPPADDING',(0,0),(-1,-1),5),('BOTTOMPADDING',(0,0),(-1,-1),5),
                ('LEFTPADDING',(0,0),(-1,-1),3),('RIGHTPADDING',(0,0),(-1,-1),3),
            ]))
            icon_cells.append(cell)
            name_cells.append(Paragraph(f'<b>{sp["name"]}</b>', ley_st))
 
        icon_row = Table([icon_cells], colWidths=[IW]*N)
        icon_row.setStyle(TableStyle([
            ('ALIGN',(0,0),(-1,-1),'CENTER'),('VALIGN',(0,0),(-1,-1),'MIDDLE'),
            ('BACKGROUND',(0,0),(-1,-1),BEIGE),
            ('BOX',(0,0),(-1,-1),1,colors.HexColor('#CCCCCC')),
            ('INNERGRID',(0,0),(-1,-1),0.5,colors.HexColor('#DDDDDD')),
            ('TOPPADDING',(0,0),(-1,-1),0),('BOTTOMPADDING',(0,0),(-1,-1),0),
            ('LEFTPADDING',(0,0),(-1,-1),0),('RIGHTPADDING',(0,0),(-1,-1),0),
        ]))
        name_row = Table([name_cells], colWidths=[IW]*N)
        name_row.setStyle(TableStyle([
            ('ALIGN',(0,0),(-1,-1),'CENTER'),('VALIGN',(0,0),(-1,-1),'MIDDLE'),
            ('BACKGROUND',(0,0),(-1,-1),VERDE_OSC),
            ('INNERGRID',(0,0),(-1,-1),0.5,colors.HexColor('#3a6b20')),
            ('TOPPADDING',(0,0),(-1,-1),3),('BOTTOMPADDING',(0,0),(-1,-1),3),
            ('LEFTPADDING',(0,0),(-1,-1),2),('RIGHTPADDING',(0,0),(-1,-1),2),
        ]))
        story.append(icon_row)
        story.append(name_row)
 
    # PÁG 2+ — Fichas
    if species_list:
        story.append(PageBreak())
        story.append(Paragraph('Fichas de especies', fic_st))
        story.append(HRFlowable(width='100%', thickness=2, color=VERDE_CLAR, spaceAfter=10))
 
        COLS = 3
        GAP  = 0.4*cm
        CW   = (PAGE_W-3*cm - GAP*(COLS-1)) / COLS
        ICO_H = 3.0*cm
        PHO_H = 4.5*cm
 
        def make_card(sp):
            hdr = Table([[Paragraph(f'<b>{sp["name"]}</b>', cnom_st)]], colWidths=[CW])
            hdr.setStyle(TableStyle([
                ('BACKGROUND',(0,0),(-1,-1),VERDE_OSC),
                ('TOPPADDING',(0,0),(-1,-1),6),('BOTTOMPADDING',(0,0),(-1,-1),6),
                ('LEFTPADDING',(0,0),(-1,-1),5),('RIGHTPADDING',(0,0),(-1,-1),5),
            ]))
            ico_img = rli(sp.get('icon'), CW-0.6*cm, ICO_H) if sp.get('icon') else None
            if ico_img:
                ico_cell = Table([[ico_img]], colWidths=[CW])
            else:
                ico_cell = Table([[dot_drawing(CW*0.5, ICO_H*0.8)]], colWidths=[CW])
            ico_cell.setStyle(TableStyle([
                ('ALIGN',(0,0),(-1,-1),'CENTER'),('VALIGN',(0,0),(-1,-1),'MIDDLE'),
                ('BACKGROUND',(0,0),(-1,-1),BEIGE),
                ('TOPPADDING',(0,0),(-1,-1),5),('BOTTOMPADDING',(0,0),(-1,-1),5),
            ]))
            pho_img = rli(sp.get('photo'), CW-0.4*cm, PHO_H) if sp.get('photo') else None
            if pho_img:
                pho_cell = Table([[pho_img]], colWidths=[CW])
                pho_cell.setStyle(TableStyle([
                    ('ALIGN',(0,0),(-1,-1),'CENTER'),('VALIGN',(0,0),(-1,-1),'MIDDLE'),
                    ('BACKGROUND',(0,0),(-1,-1),colors.HexColor('#F8F8F8')),
                    ('TOPPADDING',(0,0),(-1,-1),5),('BOTTOMPADDING',(0,0),(-1,-1),5),
                ]))
            else:
                pho_cell = None
            notes_txt = sp.get('notes','')
            if notes_txt:
                notes_cell = Table([[Paragraph(notes_txt, cnot_st)]], colWidths=[CW])
                notes_cell.setStyle(TableStyle([
                    ('BACKGROUND',(0,0),(-1,-1),BEIGE),
                    ('TOPPADDING',(0,0),(-1,-1),4),('BOTTOMPADDING',(0,0),(-1,-1),4),
                    ('LEFTPADDING',(0,0),(-1,-1),5),('RIGHTPADDING',(0,0),(-1,-1),5),
                ]))
            else:
                notes_cell = None
 
            rows = [[hdr],[ico_cell]]
            if pho_cell: rows.append([pho_cell])
            if notes_cell: rows.append([notes_cell])
 
            card = Table(rows, colWidths=[CW])
            card.setStyle(TableStyle([
                ('BOX',(0,0),(-1,-1),1,colors.HexColor('#BBBBBB')),
                ('LEFTPADDING',(0,0),(-1,-1),0),('RIGHTPADDING',(0,0),(-1,-1),0),
                ('TOPPADDING',(0,0),(-1,-1),0),('BOTTOMPADDING',(0,0),(-1,-1),0),
            ]))
            return card
 
        for i in range(0, len(species_list), COLS):
            batch = species_list[i:i+COLS]
            cards = [make_card(s) for s in batch]
            while len(cards) < COLS:
                cards.append(Spacer(CW, 1))
            row_data, widths = [], []
            for j, c in enumerate(cards):
                row_data.append(c); widths.append(CW)
                if j < COLS-1:
                    row_data.append(Spacer(GAP,1)); widths.append(GAP)
            row = Table([row_data], colWidths=widths)
            row.setStyle(TableStyle([
                ('VALIGN',(0,0),(-1,-1),'TOP'),
                ('LEFTPADDING',(0,0),(-1,-1),0),('RIGHTPADDING',(0,0),(-1,-1),0),
                ('TOPPADDING',(0,0),(-1,-1),0),('BOTTOMPADDING',(0,0),(-1,-1),10),
            ]))
            story.append(row)
 
    doc.build(story)
 
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=False)
 
