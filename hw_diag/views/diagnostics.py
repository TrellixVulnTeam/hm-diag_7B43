import json
import base64

from flask import Blueprint
from flask import render_template
from flask import request
from flask import jsonify

from hw_diag.utilities.hardware import should_display_lte
from hw_diag.utilities.miner import get_gateway_mfr_test_result
from hw_diag.utilities.miner import get_public_keys_rust
from hw_diag.utilities.hardware import get_rpi_serial
from hw_diag.utilities.hardware import get_ethernet_addresses
from hw_diag.utilities.hardware import detect_ecc
from hw_diag.utilities.hardware import lora_module_test
from hw_diag.utilities.shell import get_environment_var


DIAGNOSTICS = Blueprint('DIAGNOSTICS', __name__)


def read_diagnostics_file():
    diagnostics = {}
    try:
        with open('diagnostic_data.json', 'r') as f:
            diagnostics = json.load(f)
    except FileNotFoundError:
        msg = 'Diagnostics have not yet run, please try again in a few minutes'
        diagnostics = {'error': msg}
    return diagnostics


@DIAGNOSTICS.route('/')
def get_diagnostics():
    diagnostics = read_diagnostics_file()

    if request.args.get('json'):
        response = jsonify(diagnostics)
        response.headers.set('Content-Disposition',
                             'attachment;filename=nebra-diag.json'
                             )
        return response

    display_lte = should_display_lte(diagnostics)

    return render_template(
        'diagnostics_page.html',
        diagnostics=diagnostics,
        display_lte=display_lte
    )


@DIAGNOSTICS.route('/initFile.txt')
def get_initialisation_file():
    """
    This needs to be generated as quickly as possible,
    so we bypass the regular timer.
    """
    diagnostics = []
    get_rpi_serial(diagnostics)
    get_ethernet_addresses(diagnostics)
    get_environment_var(diagnostics)

    ecc_tests = get_gateway_mfr_test_result()

    if not ecc_tests['result'] == 'pass':
        return 'ECC tests failed', 500

    if not lora_module_test():
        return 'LoRa Module is not ready', 500

    try:
        diagnostics['OK'] = get_public_keys_rust()['key']
        diagnostics['PK'] = get_public_keys_rust()['key']
    except KeyError:
        return 'Internal Server Error', 500

    response = {
        "VA": diagnostics['VA'],
        "FR": diagnostics['FR'],
        "E0": diagnostics['E0'],
        "W0": diagnostics['W0'],
        "RPI": diagnostics['RPI'],
        "OK": diagnostics['OK'],
        "PK": diagnostics['PK'],
        "PF": diagnostics["PF"],
        "ID": diagnostics["ID"]
    }

    response_b64 = base64.b64encode(str(json.dumps(response)).encode('ascii'))
    return response_b64