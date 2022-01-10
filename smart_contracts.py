import base64

from pyteal import *
from algosdk.v2client import algod
from algosdk.future.transaction import StateSchema

def application_start():
    actions = Cond(
        [Txn.application_id() == Int(0), app_initialization()],
        [Txn.application_args[0] == Bytes("buy_nft"),
         buy_nft()],
        [Txn.application_args[0] == Bytes("place_nft_for_sale_with_royalties"),
         place_nft_for_sale_with_royalties()],
        [Txn.application_args[0] == Bytes("place_nft_for_sale"),
         place_nft_for_sale(price=Txn.application_args[1], royalty=Txn.application_args[2])],
    )
    return actions

def app_initialization():
    return Seq([
        Assert(Txn.application_args.length() == Int(2)),
        App.globalPut(Bytes("state"), Bytes("Not for sale")),
        App.globalPut(Bytes("asset_id"), Txn.assets[0]),
        App.globalPut(Bytes("owner"), Txn.application_args[0]),
        App.globalPut(Bytes("creator"), Txn.application_args[0]),
        App.globalPut(Bytes("owner_str"), Txn.application_args[1]),
        App.globalPut(Bytes("creator_str"), Txn.application_args[1]),
        Return(Int(1))
    ])

def place_nft_for_sale(price, royalty):
    valid_seller = Txn.sender() == App.globalGet(Bytes("owner"))
    valid_number_of_arguments = Txn.application_args.length() == Int(3)

    can_sell = And(valid_seller,
                   valid_number_of_arguments)

    update_state = Seq([
        App.globalPut(Bytes("state"), Bytes("On sale")),
        App.globalPut(Bytes("price"), Btoi(price)),
        App.globalPut(Bytes("royalty"), royalty),
        Return(Int(1))
    ])

    return If(can_sell).Then(update_state).Else(Return(Int(0)))

def place_nft_for_sale_with_royalties():
    valid_seller = Txn.sender() == App.globalGet(Bytes("owner"))

    can_sell = And(valid_seller)

    i = ScratchVar(TealType.uint64)
    j = ScratchVar(TealType.uint64)

    update_state = Seq([
        App.globalPut(Bytes("state"), Bytes("On sale")),
        App.globalPut(Bytes("price"), Btoi(Txn.application_args[1])),
        App.globalPut(Bytes("rs"), Btoi(Txn.application_args[2])),
        App.globalPut(Bytes("rc"), Btoi(Txn.application_args[3])),
        i.store(Int(0)),
        j.store(Int(0)),
        While(j.load() < Btoi(Txn.application_args[3])).Do(Seq([
            App.globalPut(Txn.application_args[Int(4) + i.load()], Txn.application_args[Int(5) + i.load()]),
            i.store(i.load() + Int(2)),
            j.store(j.load() + Int(1))
        ])),
        Return(Int(1))
    ])

    return If(can_sell).Then(update_state).Else(Return(Int(0)))

def buy_nft():
    is_available_for_sale = App.globalGet(Bytes("state")) == Bytes("On sale")

    valid_payment_to_seller = And(
        Gtxn[0].type_enum() == TxnType.Payment,
        Gtxn[0].receiver() == App.globalGet(Bytes("owner")),
    )

    valid_asa_transfer_from_escrow_to_buyer = And(
        Gtxn[Global.group_size() - Int(1)].type_enum() == TxnType.AssetTransfer,
        Gtxn[Global.group_size() - Int(1)].xfer_asset() == App.globalGet(Bytes("asset_id")),
        Gtxn[Global.group_size() - Int(1)].asset_amount() == Int(1)
    )

    can_buy = And(
        is_available_for_sale,
        valid_payment_to_seller,
        valid_asa_transfer_from_escrow_to_buyer
    )

    update_state = Seq([
        App.globalPut(Bytes("state"), Bytes("Not for sale")),
        App.globalPut(Bytes("owner"), Gtxn[0].sender()),
        App.globalPut(Bytes("owner_str"), Txn.application_args[1]),
        Return(Int(1))
    ])

    return If(can_buy).Then(update_state).Else(Return(Int(0)))

def approval_program():
    return application_start()

def clear_program():
    return Return(Int(1))

def compile_teal_program(client: algod.AlgodClient, source_code):
    compile_response = client.compile(source_code)
    return base64.b64decode(compile_response['result'])

def global_schema():
    return StateSchema(num_uints=10, num_byte_slices=20)

def local_schema():
    return StateSchema(num_uints=1, num_byte_slices=0)

def escrow_address_program(asset_id, app_id):
    return Seq([
        Assert(Gtxn[0].type_enum() == TxnType.Payment),
        Assert(Gtxn[Global.group_size() - Int(1)].xfer_asset() == Int(asset_id)),
        Assert(Gtxn[Global.group_size() - Int(2)].application_id() == Int(app_id)),
        Return(Int(1))
    ])