import json
import hashlib
import os
from datetime import datetime

import pandas as pd
import streamlit as st
from web3 import Web3

st.set_page_config(page_title="Evidence Registry Demo", layout="wide")
st.title("Blockchain Evidence Registry Demo")

RPC_URL = "http://127.0.0.1:8545"
CONTRACT_ADDRESS = "0x5FbDB2315678afecb367f032d93F642f64180aa3"
CHAIN_ID = 31337

DEMO_ACCOUNTS = {
    "Admin / Owner": {
        "address": "0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266",
        "private_key": "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80",
        "role_note": "Owner account with full admin access"
    },
    "High-Trust Reviewer": {
        "address": "0x3C44CdDdB6a900fa2b585dd299e03d12FA4293BC",
        "private_key": "0x5de4111afa1a4b94908f83103eb1f1706367c2e68ca870fc3fb9a804cdab365a",
        "role_note": "Authorized reviewer with score 95"
    },
    "Regular User": {
        "address": "0x90F79bf6EB2c4f870365E785982E1f101E93b906",
        "private_key": "0x7c852118294e51e653712a81e05800f419141751be58f605c371e15141b007a6",
        "role_note": "Authorized user with score 75"
    },
    "New User": {
        "address": "0x70997970C51812dc3A010C7d01b50e0d17dc79C8",
        "private_key": "0x59c6995e998f97a5a0044966f0945389dc9e86dae88c7a8412f4603b6b78690d",
        "role_note": "Authorized user with score 50"
    },
    "Unauthorized Outsider": {
        "address": "0x15d34AAf54267DB7D7c367839AAf71A00a2C6A65",
        "private_key": "0x47e179ec197488593b187f80a00eb0da91f1b9d0b13f8733639f19c30a34926a",
        "role_note": "Not authorized, should fail on submission"
    },
}

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ARTIFACT_PATH = os.path.join(
    BASE_DIR,
    "..",
    "artifacts",
    "contracts",
    "EvidenceRegistry.sol",
    "EvidenceRegistry.json",
)
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

selected_user_label = st.sidebar.selectbox("Choose demo account", list(DEMO_ACCOUNTS.keys()))
selected_user = DEMO_ACCOUNTS[selected_user_label]
PRIVATE_KEY = selected_user["private_key"]

st.sidebar.write(f"Role note: {selected_user['role_note']}")
st.sidebar.code(selected_user["address"], language=None)

with open(ARTIFACT_PATH, "r") as f:
    artifact_json = json.load(f)
    contract_abi = artifact_json["abi"]

w3 = Web3(Web3.HTTPProvider(RPC_URL))

if not w3.is_connected():
    st.error("Not connected to Hardhat local blockchain.")
    st.stop()

if CONTRACT_ADDRESS == "PASTE_NEW_CONTRACT_ADDRESS_HERE":
    st.warning("Please paste your new deployed contract address into app.py")
    st.stop()

account = w3.eth.account.from_key(PRIVATE_KEY)
wallet_address = account.address

contract = w3.eth.contract(
    address=Web3.to_checksum_address(CONTRACT_ADDRESS),
    abi=contract_abi
)

owner_address = contract.functions.owner().call()


def generate_file_hash(uploaded_file):
    file_bytes = uploaded_file.getvalue()
    return hashlib.sha256(file_bytes).hexdigest()


def send_transaction(function_call):
    nonce = w3.eth.get_transaction_count(wallet_address)

    tx = function_call.build_transaction({
        "from": wallet_address,
        "nonce": nonce,
        "gas": 4000000,
        "gasPrice": w3.to_wei("2", "gwei"),
        "chainId": CHAIN_ID,
    })

    signed_tx = w3.eth.account.sign_transaction(tx, PRIVATE_KEY)
    tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash)

    return tx_hash.hex(), receipt


def save_uploaded_file(uploaded_file, evidence_id):
    safe_name = uploaded_file.name.replace("/", "_").replace("\\", "_")
    file_path = os.path.join(UPLOAD_DIR, f"{evidence_id}_{safe_name}")

    with open(file_path, "wb") as f:
        f.write(uploaded_file.getvalue())

    return file_path


def status_label(status_code):
    mapping = {
        0: "Pending",
        1: "Approved",
        2: "Rejected"
    }
    return mapping.get(status_code, "Unknown")


def get_wallet_score(address):
    return contract.functions.trustScores(address).call()


def is_owner():
    return wallet_address.lower() == owner_address.lower()


def can_review():
    try:
        return is_owner() or get_wallet_score(wallet_address) >= 90
    except Exception:
        return False


def get_user_stats(address):
    stats = contract.functions.getUserStats(address).call()
    return {
        "authorized": stats[0],
        "score": stats[1],
        "approved": stats[2],
        "rejected": stats[3],
        "pending": stats[4],
        "total_uploads": stats[5],
    }


def get_evidence_record(evidence_id):
    e = contract.functions.getEvidence(evidence_id).call()
    return {
        "id": e[0],
        "case_id": e[1],
        "file_hash": e[2],
        "file_name": e[3],
        "uploader": e[4],
        "timestamp": datetime.fromtimestamp(e[5]),
        "status_code": e[6],
        "status": status_label(e[6]),
        "reviewed_by": e[7],
        "reviewed_at": datetime.fromtimestamp(e[8]) if e[8] > 0 else None,
        "review_note": e[9],
    }


def get_all_evidence_records():
    ids = contract.functions.getAllEvidenceIds().call()
    records = []

    for evidence_id in ids:
        try:
            records.append(get_evidence_record(evidence_id))
        except Exception:
            pass

    records.sort(key=lambda x: x["id"], reverse=True)
    return records


def setup_demo_users():
    demo_plan = [
        ("New User", "0x70997970C51812dc3A010C7d01b50e0d17dc79C8", 50, True),
        ("High-Trust Reviewer", "0x3C44CdDdB6a900fa2b585dd299e03d12FA4293BC", 95, True),
        ("Regular User", "0x90F79bf6EB2c4f870365E785982E1f101E93b906", 75, True),
        ("Unauthorized Outsider", "0x15d34AAf54267DB7D7c367839AAf71A00a2C6A65", 0, False),
    ]

    results = []

    for label, address, score, should_authorize in demo_plan:
        try:
            if should_authorize:
                send_transaction(
                    contract.functions.authorizeUser(Web3.to_checksum_address(address))
                )
            send_transaction(
                contract.functions.adminSetTrustScore(
                    Web3.to_checksum_address(address),
                    score
                )
            )
            if not should_authorize:
                try:
                    send_transaction(
                        contract.functions.revokeUser(Web3.to_checksum_address(address))
                    )
                except Exception:
                    pass

            results.append(f"{label}: configured successfully")
        except Exception as e:
            results.append(f"{label}: {str(e)}")

    return results


st.success("Connected to blockchain")
st.write(f"Current wallet: {wallet_address}")
st.write(f"Current demo role: {selected_user_label}")
st.write(f"Owner address: {owner_address}")

try:
    current_score = get_wallet_score(wallet_address)
    stats = get_user_stats(wallet_address)
except Exception:
    current_score = 0
    stats = {
        "approved": 0,
        "rejected": 0,
        "pending": 0,
        "authorized": False,
        "score": 0,
        "total_uploads": 0,
    }

col_a, col_b, col_c, col_d = st.columns(4)
col_a.metric("My Score", current_score)
col_b.metric("Approved", stats["approved"])
col_c.metric("Rejected", stats["rejected"])
col_d.metric("Pending", stats["pending"])

if current_score < 70:
    st.info("This account's submissions will go to review until the score reaches 70.")
elif current_score >= 90:
    st.success("This account can review pending evidence.")
else:
    st.success("This account's submissions are auto-approved.")

tab1, tab2, tab3 = st.tabs(["Submit Evidence", "Verify / History", "Admin / Review"])

with tab1:
    st.subheader("Submit Evidence")

    case_id = st.text_input("Case ID")
    uploaded_file = st.file_uploader("Upload file", key="submit_file")

    if uploaded_file is not None:
        file_hash = generate_file_hash(uploaded_file)
        st.write("Generated SHA-256 Hash:")
        st.code(file_hash)

    if st.button("Submit Evidence"):
        if not case_id:
            st.error("Please enter a Case ID.")
        elif uploaded_file is None:
            st.error("Please upload a file.")
        else:
            try:
                next_id = contract.functions.nextEvidenceId().call()
                file_hash = generate_file_hash(uploaded_file)

                tx_hash, receipt = send_transaction(
                    contract.functions.submitEvidence(
                        case_id,
                        file_hash,
                        uploaded_file.name
                    )
                )

                saved_path = save_uploaded_file(uploaded_file, next_id)
                new_record = get_evidence_record(next_id)

                st.success("Evidence submitted successfully.")
                st.write(f"Evidence ID: {next_id}")
                st.write(f"Transaction Hash: {tx_hash}")
                st.write(f"Block Number: {receipt.blockNumber}")
                st.write(f"Submission Status: {new_record['status']}")
                st.write(f"Saved Locally At: {saved_path}")

            except Exception as e:
                st.error(f"Transaction failed: {str(e)}")

with tab2:
    st.subheader("Verify Evidence")

    verify_case_id = st.text_input("Case ID to verify")

    case_ids = []
    if verify_case_id:
        try:
            case_ids = contract.functions.getEvidenceIdsByCase(verify_case_id).call()
        except Exception as e:
            st.error(f"Could not fetch case evidence: {str(e)}")

    selected_evidence_id = None
    if case_ids:
        selected_evidence_id = st.selectbox(
            "Select Evidence ID",
            case_ids,
            format_func=lambda x: f"Evidence #{x}"
        )

    verify_file = st.file_uploader("Upload file for verification", key="verify_file")

    if verify_file is not None:
        verify_hash = generate_file_hash(verify_file)
        st.write("Generated SHA-256 Hash:")
        st.code(verify_hash)

    if st.button("Verify Evidence"):
        if not verify_case_id:
            st.error("Please enter a Case ID.")
        elif not case_ids:
            st.error("No evidence found for this Case ID.")
        elif verify_file is None:
            st.error("Please upload a file.")
        else:
            try:
                verify_hash = generate_file_hash(verify_file)
                evidence = get_evidence_record(selected_evidence_id)

                is_valid = contract.functions.verifyEvidence(
                    selected_evidence_id,
                    verify_hash
                ).call()

                st.write("Stored Evidence Details:")
                st.write(f"Evidence ID: {evidence['id']}")
                st.write(f"Case ID: {evidence['case_id']}")
                st.write(f"File Name: {evidence['file_name']}")
                st.write(f"Stored Hash: {evidence['file_hash']}")
                st.write(f"Uploader: {evidence['uploader']}")
                st.write(f"Timestamp: {evidence['timestamp']}")
                st.write(f"Status: {evidence['status']}")
                st.write(f"Review Note: {evidence['review_note']}")

                if is_valid:
                    st.success("Valid evidence: file matches blockchain record.")
                else:
                    st.error("Invalid evidence: file does not match blockchain record.")

            except Exception as e:
                st.error(f"Verification failed: {str(e)}")

    st.divider()
    st.subheader("Previous Uploads")

    try:
        history = get_all_evidence_records()
        if history:
            history_df = pd.DataFrame(history)
            st.dataframe(history_df, use_container_width=True)
        else:
            st.info("No uploads yet.")
    except Exception as e:
        st.error(f"Could not load history: {str(e)}")

with tab3:
    st.subheader("Admin / Review Panel")

    st.write(f"My Review Permission: {'Yes' if can_review() else 'No'}")

    if is_owner():
        st.markdown("### Demo Setup")

        if st.button("Setup Demo Users"):
            results = setup_demo_users()
            for r in results:
                st.write(r)

        st.divider()
        st.markdown("### Authorize or Revoke User")
        user_address = st.text_input("User Address")

        col1, col2 = st.columns(2)

        with col1:
            if st.button("Authorize User"):
                if not user_address:
                    st.error("Please enter a user address.")
                else:
                    try:
                        tx_hash, _ = send_transaction(
                            contract.functions.authorizeUser(
                                Web3.to_checksum_address(user_address)
                            )
                        )
                        st.success("User authorized.")
                        st.write(f"Transaction Hash: {tx_hash}")
                    except Exception as e:
                        st.error(f"Authorization failed: {str(e)}")

        with col2:
            if st.button("Revoke User"):
                if not user_address:
                    st.error("Please enter a user address.")
                else:
                    try:
                        tx_hash, _ = send_transaction(
                            contract.functions.revokeUser(
                                Web3.to_checksum_address(user_address)
                            )
                        )
                        st.success("User revoked.")
                        st.write(f"Transaction Hash: {tx_hash}")
                    except Exception as e:
                        st.error(f"Revoke failed: {str(e)}")

    st.divider()
    st.markdown("### User Scores")

    try:
        users = contract.functions.getRegisteredUsers().call()
        user_rows = []

        for user in users:
            s = get_user_stats(user)
            role = "Custom"
            for label, info in DEMO_ACCOUNTS.items():
                if info["address"].lower() == user.lower():
                    role = label

            user_rows.append({
                "role": role,
                "wallet": user,
                "authorized": s["authorized"],
                "score": s["score"],
                "approved": s["approved"],
                "rejected": s["rejected"],
                "pending": s["pending"],
                "total_uploads": s["total_uploads"],
                "can_review": s["score"] >= 90
            })

        if user_rows:
            st.dataframe(pd.DataFrame(user_rows), use_container_width=True)
        else:
            st.info("No users found.")
    except Exception as e:
        st.error(f"Could not load users: {str(e)}")

    st.divider()
    st.markdown("### Review Pending Evidence")

    if can_review():
        try:
            all_records = get_all_evidence_records()
            pending_records = [r for r in all_records if r["status_code"] == 0]

            if pending_records:
                pending_options = [r["id"] for r in pending_records]
                selected_pending_id = st.selectbox(
                    "Select pending evidence",
                    pending_options,
                    format_func=lambda x: f"Evidence #{x}"
                )

                selected_record = next(r for r in pending_records if r["id"] == selected_pending_id)

                st.write(f"Case ID: {selected_record['case_id']}")
                st.write(f"File Name: {selected_record['file_name']}")
                st.write(f"Uploader: {selected_record['uploader']}")
                st.write(f"Timestamp: {selected_record['timestamp']}")
                st.write(f"Hash: {selected_record['file_hash']}")

                review_note = st.text_area("Review note", key="review_note")

                review_col1, review_col2 = st.columns(2)

                with review_col1:
                    if st.button("Approve Evidence"):
                        try:
                            tx_hash, _ = send_transaction(
                                contract.functions.reviewEvidence(
                                    selected_pending_id,
                                    True,
                                    review_note
                                )
                            )
                            st.success("Evidence approved.")
                            st.write(f"Transaction Hash: {tx_hash}")
                        except Exception as e:
                            st.error(f"Approval failed: {str(e)}")

                with review_col2:
                    if st.button("Reject Evidence"):
                        try:
                            tx_hash, _ = send_transaction(
                                contract.functions.reviewEvidence(
                                    selected_pending_id,
                                    False,
                                    review_note
                                )
                            )
                            st.success("Evidence rejected.")
                            st.write(f"Transaction Hash: {tx_hash}")
                        except Exception as e:
                            st.error(f"Rejection failed: {str(e)}")
            else:
                st.info("No pending evidence right now.")
        except Exception as e:
            st.error(f"Could not load pending evidence: {str(e)}")
    else:
        st.warning("Only the owner or users with score 90+ can review evidence.")