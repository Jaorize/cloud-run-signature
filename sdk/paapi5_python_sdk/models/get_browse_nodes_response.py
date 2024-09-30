# coding: utf-8

"""
  Copyright 2020 Amazon.com, Inc. or its affiliates. All Rights Reserved.

  Licensed under the Apache License, Version 2.0 (the "License").
  You may not use this file except in compliance with the License.
  A copy of the License is located at

      http://www.apache.org/licenses/LICENSE-2.0

  or in the "license" file accompanying this file. This file is distributed
  on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either
  express or implied. See the License for the specific language governing
  permissions and limitations under the License.
"""


"""
    ProductAdvertisingAPI

    https://webservices.amazon.com/paapi5/documentation/index.html  # noqa: E501
"""


import pprint
import re  # noqa: F401

import six

from paapi5_python_sdk.models.browse_nodes_result import BrowseNodesResult  # noqa: F401,E501
from paapi5_python_sdk.models.error_data import ErrorData  # noqa: F401,E501


class GetBrowseNodesResponse(object):
    """NOTE: This class is auto generated by the swagger code generator program.

    Do not edit the class manually.
    """

    """
    Attributes:
      swagger_types (dict): The key is attribute name
                            and the value is attribute type.
      attribute_map (dict): The key is attribute name
                            and the value is json key in definition.
    """
    swagger_types = {
        'browse_nodes_result': 'BrowseNodesResult',
        'errors': 'list[ErrorData]'
    }

    attribute_map = {
        'browse_nodes_result': 'BrowseNodesResult',
        'errors': 'Errors'
    }

    def __init__(self, browse_nodes_result=None, errors=None):  # noqa: E501
        """GetBrowseNodesResponse - a model defined in Swagger"""  # noqa: E501

        self._browse_nodes_result = None
        self._errors = None
        self.discriminator = None

        if browse_nodes_result is not None:
            self.browse_nodes_result = browse_nodes_result
        if errors is not None:
            self.errors = errors

    @property
    def browse_nodes_result(self):
        """Gets the browse_nodes_result of this GetBrowseNodesResponse.  # noqa: E501


        :return: The browse_nodes_result of this GetBrowseNodesResponse.  # noqa: E501
        :rtype: BrowseNodesResult
        """
        return self._browse_nodes_result

    @browse_nodes_result.setter
    def browse_nodes_result(self, browse_nodes_result):
        """Sets the browse_nodes_result of this GetBrowseNodesResponse.


        :param browse_nodes_result: The browse_nodes_result of this GetBrowseNodesResponse.  # noqa: E501
        :type: BrowseNodesResult
        """

        self._browse_nodes_result = browse_nodes_result

    @property
    def errors(self):
        """Gets the errors of this GetBrowseNodesResponse.  # noqa: E501


        :return: The errors of this GetBrowseNodesResponse.  # noqa: E501
        :rtype: list[ErrorData]
        """
        return self._errors

    @errors.setter
    def errors(self, errors):
        """Sets the errors of this GetBrowseNodesResponse.


        :param errors: The errors of this GetBrowseNodesResponse.  # noqa: E501
        :type: list[ErrorData]
        """

        self._errors = errors

    def to_dict(self):
        """Returns the model properties as a dict"""
        result = {}

        for attr, _ in six.iteritems(self.swagger_types):
            value = getattr(self, attr)
            if isinstance(value, list):
                result[attr] = list(map(
                    lambda x: x.to_dict() if hasattr(x, "to_dict") else x,
                    value
                ))
            elif hasattr(value, "to_dict"):
                result[attr] = value.to_dict()
            elif isinstance(value, dict):
                result[attr] = dict(map(
                    lambda item: (item[0], item[1].to_dict())
                    if hasattr(item[1], "to_dict") else item,
                    value.items()
                ))
            else:
                result[attr] = value
        if issubclass(GetBrowseNodesResponse, dict):
            for key, value in self.items():
                result[key] = value

        return result

    def to_str(self):
        """Returns the string representation of the model"""
        return pprint.pformat(self.to_dict())

    def __repr__(self):
        """For `print` and `pprint`"""
        return self.to_str()

    def __eq__(self, other):
        """Returns true if both objects are equal"""
        if not isinstance(other, GetBrowseNodesResponse):
            return False

        return self.__dict__ == other.__dict__

    def __ne__(self, other):
        """Returns true if both objects are not equal"""
        return not self == other
