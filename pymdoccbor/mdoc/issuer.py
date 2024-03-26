import binascii
import cbor2
import logging

from pycose.keys import CoseKey, EC2Key
from typing import Union, List

from pymdoccbor.mso.issuer import MsoIssuer
from pymdoccbor.mdoc.exceptions import MissingPrivateKey

logger = logging.getLogger('pymdoccbor')


class MdocCborIssuer:
    """
    MdocCborIssuer helper class to create a new mdoc
    """

    def __init__(self, private_key: Union[dict, EC2Key, CoseKey]):
        """
        Create a new MdocCborIssuer instance

        :param private_key: the private key to sign the mdoc
        :type private_key: dict | CoseKey

        :raises MissingPrivateKey: if no private key is provided
        """
        self.version: str = '1.0'
        self.status: int = 0

        if isinstance(private_key, dict):
            self.private_key = CoseKey.from_dict(private_key)
        elif isinstance(private_key, EC2Key):
            ec2_encoded = private_key.encode()
            ec2_decoded = CoseKey.decode(ec2_encoded)
            self.private_key = ec2_decoded
        elif isinstance(private_key, CoseKey):
            self.private_key = private_key
        else:
            raise MissingPrivateKey("You must provide a private key")

        
        self.signed :dict = {}

    def new(
        self,
        data: Union[dict, List[dict]],
        devicekeyinfo: Union[dict, CoseKey],
        doctype: Union[str, None] = None
    ) -> dict:
        """
        create a new mdoc with signed mso

        :param data: the data to sign
        Can be a dict, representing the single document, or a list of dicts containg the doctype and the data
        Example:
        {doctype: "org.iso.18013.5.1.mDL", data: {...}}
        :type data: dict | list[dict]
        :param devicekeyinfo: the device key info
        :type devicekeyinfo: dict | CoseKey
        :param doctype: the document type (optional if data is a list)
        :type doctype: str | None

        :return: the signed mdoc
        :rtype: dict
        """
        if isinstance(devicekeyinfo, dict):
            devicekeyinfo = CoseKey.from_dict(devicekeyinfo)
        else:
            devicekeyinfo: CoseKey = devicekeyinfo

        if isinstance(data, dict):
            data = [{"doctype": doctype, "data": data}]

        documents = []

        for doc in data:
            msoi = MsoIssuer(
                data=doc["data"],
                private_key=self.private_key
            )

            mso = msoi.sign()

            document = {
                'docType': doc["doctype"],  # 'org.iso.18013.5.1.mDL'
                'issuerSigned': {
                    "nameSpaces": {
                        ns: [
                            cbor2.CBORTag(24, value={k: v}) for k, v in dgst.items()
                        ]
                        for ns, dgst in msoi.disclosure_map.items()
                    },
                    "issuerAuth": mso.encode()
                },
                # this is required during the presentation.
                #  'deviceSigned': {
                    #  # TODO
                #  }
            }

            documents.append(document)

        self.signed = {
            'version': self.version,
            'documents': documents,
            'status': self.status
        }
        return self.signed
    
    def dump(self):
        """
        Returns the signed mdoc in CBOR format

        :return: the signed mdoc in CBOR format
        :rtype: bytes
        """
        return cbor2.dumps(self.signed)

    def dumps(self):
        """
        Returns the signed mdoc in AF binary repr

        :return: the signed mdoc in AF binary repr
        :rtype: bytes
        """
        return binascii.hexlify(cbor2.dumps(self.signed))
