import algosdk.encoding
from algosdk.constants import PAYMENT_TXN, APPCALL_TXN, ASSETTRANSFER_TXN
from flask import Flask, request, jsonify, render_template, Response, session, url_for, redirect
import ipfshttpclient
import os, tempfile, mimetypes
from algosdk import mnemonic, account
from algosdk.future.transaction import OnComplete, ApplicationCallTxn, PaymentTxn, AssetTransferTxn, calculate_group_id, AssetConfigTxn, LogicSig, LogicSigTransaction
import algorand
import royalties

api = Flask(__name__)
api.secret_key = os.urandom(24)

@api.route('/')
def index():
    #session['publickey'] = 'EV5PYVBEVS4PPWAWO3JJQIHD3L36BA5DS5RH34FGTVLUQW6Y3JVWTWM64Y'
    if session.get("publickey"):
        return redirect("/myassets")
    return render_template('index.html')

@api.route('/login', methods=['POST'])
def login():
    try:
        public_key = request.json['publickey']
        passphrase = request.json['passphrase']
        private_key = algorand.get_private_key_from_mnemonic(passphrase)
        public_key_from_passphrase = account.address_from_private_key(private_key)
        if (public_key_from_passphrase != public_key):
            return Response(
                "Unauthoried",
                status=401,
            )
        session['publickey'] = public_key
        return redirect(url_for('myassets'), code=302)
    except Exception as e:
        return Response(
            "Unauthoried, {0}".format(e),
            status=401,
        )

@api.route('/logout', methods=['POST'])
def logout():
    if not session.get("publickey"):
        return redirect("/")
    session.pop('publickey', None)
    return redirect('/')

@api.route('/myassets')
def myassets():
    if not session.get("publickey"):
        return redirect("/")
    return render_template('myassets.html')

@api.route('/createasset')
def createasset():
    if not session.get("publickey"):
        return redirect("/")
    return render_template('createasset.html')

@api.route('/marketplace')
def marketplace():
    if not session.get("publickey"):
        return redirect("/")
    return render_template('marketplace.html')

@api.route('/mytransactions')
def mytransactions():
    if not session.get("publickey"):
        return redirect("/")
    return render_template('mytransactions.html')

@api.route('/generateAccount', methods=['GET'])
def generate_account():
    acct = account.generate_account()
    return jsonify(
        publickey=acct[1],
        passphrase=mnemonic.from_private_key(acct[0])
    )

@api.route('/getaccountinfo', methods=['GET'])
def get_account_info():
    try:
        if not session.get("publickey"):
            return redirect("/")
        indexer_client = algorand.get_indexer_client()
        result = indexer_client.account_info(address=session.get("publickey"))
        return jsonify(
            accountinfo=result,
        )
    except Exception as e:
        return Response(
            str(e),
            status=400,
        )

@api.route('/getassets', methods=['GET'])
def get_assets():
    try:
        if not session.get("publickey"):
            return redirect("/")
        indexer_client = algorand.get_indexer_client()
        result = indexer_client.search_applications()
        return jsonify(
            assets=algorand.get_assets_from_applications(result['applications']),
        )
    except Exception as e:
        return Response(
            str(e),
            status=400,
        )

@api.route('/getmyassets', methods=['GET'])
def get_my_assets():
    try:
        if not session.get("publickey"):
            return redirect("/")
        algod_client = algorand.get_algod_client()
        account_info = algod_client.account_info(address=session.get("publickey"))
        foreign_accouns = {}
        my_assets_ids = {}
        for asset in account_info['assets']:
            if asset['amount'] > 0:
                foreign_accouns[asset['creator']] = True
                my_assets_ids[asset['asset-id']] = True

        foreign_assets = []
        for key in foreign_accouns:
            foreign_account_info = algod_client.account_info(address=key)
            assets = algorand.get_assets_from_applications(foreign_account_info['created-apps'])
            foreign_assets = foreign_assets + assets
        my_assets = []
        for asset in foreign_assets:
            if int(asset['asset_id']) in my_assets_ids:
                my_assets.append(asset)
        return jsonify(
            assets=my_assets
        )
    except Exception as e:
        return Response(
            str(e),
            status=400,
        )

@api.route('/getassetinfo', methods=['GET'])
def get_asset_info():
    try:
        if not session.get("publickey"):
            return redirect("/")
        asset_id = int(request.args['asset_id'])
        result = algorand.get_algod_client().asset_info(asset_id=asset_id)
        return jsonify(
            assetinfo=result,
        )
    except Exception as e:
        return Response(
            str(e),
            status=400,
        )

@api.route('/gettransactions', methods=['GET'])
def gettransactions():
    try:
        if not session.get("publickey"):
            return redirect("/")
        result = algorand.get_indexer_client().search_transactions_by_address(address=session.get("publickey"), txn_type="pay")
        return jsonify(
            transactions=result,
        )
    except Exception as e:
        return Response(
            str(e),
            status=400,
        )

@api.route('/getappinfo', methods=['GET'])
def get_app_info():
    try:
        if not session.get("publickey"):
            return redirect("/")
        application_id = int(request.args['app_id'])
        result = algorand.get_algod_client().application_info(application_id=application_id)
        return jsonify(
            appinfo=result,
        )
    except Exception as e:
        return Response(
            str(e),
            status=400,
        )

@api.route('/uploadToIPFS', methods=['POST'])
def upload_to_ipfs():
    if not session.get("publickey"):
        return redirect("/")
    file = request.files['file']
    extension = mimetypes.guess_extension(file.content_type, strict=True)
    tmp = tempfile.NamedTemporaryFile(suffix=extension, delete=False)
    try:
        client = ipfshttpclient.connect()
        data = file.stream.read()
        tmp.write(data)
        res = client.add(tmp.name)
        return jsonify(
            hash=res['Hash'],
            name=res['Name'],
            url='http://127.0.0.1:8080/ipfs/{0}'.format(res['Hash'])
        )
    except Exception as e:
        return Response(
            str(e),
            status=400,
        )
    finally:
        tmp.close()
        os.unlink(tmp.name)

@api.route('/createNFT', methods=['POST'])
def create_nft():
    try:
        if not session.get("publickey"):
            return redirect("/")
        nft_metadata = request.json['nftMetadata']
        passphrase = request.json['passphrase']
        private_key = algorand.get_private_key_from_mnemonic(passphrase)
        public_key = account.address_from_private_key(private_key)
        assetid, txid = algorand.create_non_fungible_token(public_key, private_key, nft_metadata)
        appid = algorand.create_application(passphrase, assetid)
        return redirect(url_for('myassets'), code=302)
    except Exception as e:
        return Response(
            "Error executing API: {}".format(e),
            status=400,
        )

@api.route('/listNFTs', methods=['GET'])
def list_nfts():
    try:
        public_key = request.args['publicKey']
        asset_id = request.args['assetId']
        result = algorand.get_indexer_client().search_assets(asset_id=asset_id)
        return jsonify(
            nftList=result,
        )
    except Exception as e:
        return Response(
            str(e),
            status=400,
        )

@api.route('/placeNFTForSale', methods=['POST'])
def place_nft_for_sale():
    try:
        if not session.get("publickey"):
            return redirect("/")
        passphrase = request.json['passphrase']
        app_id = request.json['app_id']
        asset_id = request.json['asset_id']
        price = request.json['price']
        royalty = request.json['royalty']
        signin_key = algorand.get_private_key_from_mnemonic(passphrase)
        public_key = account.address_from_private_key(signin_key)

        algod_client = algorand.get_algod_client()

        royalty_args = royalties.get_new_royalty_structure_arguments(public_key, royalty['state'],
                                                                     royalty['royalty_groups'], royalty['chain_groups'])
        result = algorand.get_algod_client().application_info(application_id=app_id)
        asset = algorand.get_assets_from_applications([result])[0]

        if asset['creator_str'] != public_key:
            royalty_args = royalties.get_new_royalty_structure_arguments(asset['owner_str'], asset['royalty']['state'],
                                                                         asset['royalty']['royalty_groups'],
                                                                         asset['royalty']['chain_groups'])

        if royalty['state'] == royalties.CHAIN and 'royalty' in asset:
            royalty_args = royalties.get_new_royalty_structure_arguments(public_key, asset['royalty']['state'],
                                                                         asset['royalty']['royalty_groups'],
                                                                         asset['royalty']['chain_groups'])

        app_args = [
            "place_nft_for_sale_with_royalties",
            price,
        ]

        app_args = app_args + royalty_args

        params = algod_client.suggested_params()

        txn1 = ApplicationCallTxn(sender=public_key,
                                 sp=params,
                                 index=app_id,
                                 app_args=app_args,
                                 on_complete=OnComplete.NoOpOC)

        escrow_address = algorand.get_escrow_address(asset_id, app_id)

        txn3 = PaymentTxn(sender=public_key,
                          sp=params,
                          receiver=escrow_address,
                          amt=1000000)
        txns = []
        txns.append(txn1)
        txns.append(txn3)

        if asset['creator_str'] == public_key:
            txn2 = AssetConfigTxn(
                sender=public_key,
                sp=params,
                index=asset_id,
                default_frozen=False,
                manager=public_key,
                reserve=public_key,
                freeze=public_key,
                clawback=escrow_address,
                strict_empty_address_check=False)
            txns.append(txn2)

        group_id = calculate_group_id(txns)

        stxns = []
        for txn in txns:
            txn.group = group_id
            stxn = txn.sign(signin_key)
            stxns.append(stxn)

        txid = algod_client.send_transactions(stxns)
        algorand.wait_for_confirmation(algod_client, txid, 4)
        return redirect(url_for('myassets'), code=302)
    except Exception as e:
        return Response(
            str(e),
            status=400,
        )

@api.route('/buyNFT', methods=['POST'])
def buy_nft():
    try:
        if not session.get("publickey"):
            return redirect("/")
        passphrase = request.json['passphrase']
        app_id = request.json['app_id']
        asset_id = request.json['asset_id']
        signin_key = algorand.get_private_key_from_mnemonic(passphrase)
        public_key = account.address_from_private_key(signin_key)

        result = algorand.get_algod_client().application_info(application_id=app_id)
        asset = algorand.get_assets_from_applications([result])[0]

        algod_client = algorand.get_algod_client()

        app_args = [
            "buy_nft",
            public_key
        ]

        params = algod_client.suggested_params()

        txn = AssetTransferTxn(sender=public_key,
                               sp=params,
                               receiver=public_key,
                               amt=0,
                               index=asset_id)

        stxn = txn.sign(signin_key)
        txid = algod_client.send_transaction(stxn)
        algorand.wait_for_confirmation(algod_client, txid, 4)

        escrow_address = algorand.get_escrow_address(asset_id, app_id)
        logic_sign_in_key = algorand.get_escrow_signature(asset_id, app_id)

        txn1 = ApplicationCallTxn(sender=public_key,
                                 sp=params,
                                 index=app_id,
                                 app_args=app_args,
                                 on_complete=OnComplete.NoOpOC)

        txns = royalties.get_royalty_transactions(asset['royalty'], public_key, asset['owner_str'], asset['price'], params)

        txn3 = AssetTransferTxn(sender=escrow_address,
                                sp=params,
                                receiver=public_key,
                                amt=1,
                                index=asset_id,
                                revocation_target=asset['owner_str'])

        txns.append(txn1)
        txns.append(txn3)

        group_id = calculate_group_id(txns)

        stxns = []
        for txn in txns:
            txn.group = group_id
            if txn.type == PAYMENT_TXN:
                stxn = txn.sign(signin_key)
                stxns.append(stxn)
                continue
            if txn.type == APPCALL_TXN:
                stxn = txn.sign(signin_key)
                stxns.append(stxn)
                continue
            if txn.type == ASSETTRANSFER_TXN:
                stxn = LogicSigTransaction(txn, logic_sign_in_key)
                stxns.append(stxn)
                continue

        txid = algod_client.send_transactions(stxns)
        algorand.wait_for_confirmation(algod_client, txid, 4)
        return redirect(url_for('myassets'), code=302)
    except Exception as e:
        return Response(
            str(e),
            status=400,
        )

if __name__ == '__main__':
    api.run()