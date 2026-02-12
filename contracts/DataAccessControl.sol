// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract DataAccessControl {
    // Struct to store access request details
    struct AccessRequest {
        uint256 requestId;
        address userAddress;
        string username;
        string dataId;
        string dataName;
        uint256 timestamp;
        bool approved;
        bool processed;
        address approvedBy;
        uint256 approvalTimestamp;
    }
    
    // Struct to store data upload records
    struct DataRecord {
        string dataId;
        string dataName;
        address uploadedBy;
        uint256 uploadTimestamp;
        string ipfsHash; // For future IPFS integration
        bool active;
    }
    
    // Struct to store access logs
    struct AccessLog {
        uint256 logId;
        address userAddress;
        string username;
        string dataId;
        uint256 accessTimestamp;
        string action; // "view", "download", etc.
    }
    
    // State variables
    address public admin;
    uint256 public requestCounter;
    uint256 public logCounter;
    
    // Mappings
    mapping(uint256 => AccessRequest) public accessRequests;
    mapping(string => DataRecord) public dataRecords;
    mapping(uint256 => AccessLog) public accessLogs;
    mapping(address => uint256[]) public userRequests;
    mapping(string => uint256[]) public dataAccessLogs;
    
    // Events
    event RequestCreated(uint256 indexed requestId, address indexed user, string dataId, uint256 timestamp);
    event RequestProcessed(uint256 indexed requestId, bool approved, address indexed approvedBy, uint256 timestamp);
    event DataUploaded(string indexed dataId, string dataName, address indexed uploadedBy, uint256 timestamp);
    event DataAccessed(uint256 indexed logId, address indexed user, string dataId, uint256 timestamp);
    event DataModified(string indexed dataId, address indexed modifiedBy, uint256 timestamp);
    event DataDeleted(string indexed dataId, address indexed deletedBy, uint256 timestamp);
    
    // Modifiers
    modifier onlyAdmin() {
        require(msg.sender == admin, "Only admin can perform this action");
        _;
    }
    
    constructor() {
        admin = msg.sender;
        requestCounter = 0;
        logCounter = 0;
    }
    
    // Create a new access request
    function createAccessRequest(
        address _userAddress,
        string memory _username,
        string memory _dataId,
        string memory _dataName
    ) public returns (uint256) {
        requestCounter++;
        
        accessRequests[requestCounter] = AccessRequest({
            requestId: requestCounter,
            userAddress: _userAddress,
            username: _username,
            dataId: _dataId,
            dataName: _dataName,
            timestamp: block.timestamp,
            approved: false,
            processed: false,
            approvedBy: address(0),
            approvalTimestamp: 0
        });
        
        userRequests[_userAddress].push(requestCounter);
        
        emit RequestCreated(requestCounter, _userAddress, _dataId, block.timestamp);
        
        return requestCounter;
    }
    
    // Process access request (approve/reject)
    function processAccessRequest(uint256 _requestId, bool _approved) public onlyAdmin {
        require(_requestId > 0 && _requestId <= requestCounter, "Invalid request ID");
        require(!accessRequests[_requestId].processed, "Request already processed");
        
        accessRequests[_requestId].approved = _approved;
        accessRequests[_requestId].processed = true;
        accessRequests[_requestId].approvedBy = msg.sender;
        accessRequests[_requestId].approvalTimestamp = block.timestamp;
        
        emit RequestProcessed(_requestId, _approved, msg.sender, block.timestamp);
    }
    
    // Record data upload
    function recordDataUpload(
        string memory _dataId,
        string memory _dataName,
        address _uploadedBy,
        string memory _ipfsHash
    ) public onlyAdmin {
        dataRecords[_dataId] = DataRecord({
            dataId: _dataId,
            dataName: _dataName,
            uploadedBy: _uploadedBy,
            uploadTimestamp: block.timestamp,
            ipfsHash: _ipfsHash,
            active: true
        });
        
        emit DataUploaded(_dataId, _dataName, _uploadedBy, block.timestamp);
    }
    
    // Log data access
    function logDataAccess(
        address _userAddress,
        string memory _username,
        string memory _dataId,
        string memory _action
    ) public returns (uint256) {
        logCounter++;
        
        accessLogs[logCounter] = AccessLog({
            logId: logCounter,
            userAddress: _userAddress,
            username: _username,
            dataId: _dataId,
            accessTimestamp: block.timestamp,
            action: _action
        });
        
        dataAccessLogs[_dataId].push(logCounter);
        
        emit DataAccessed(logCounter, _userAddress, _dataId, block.timestamp);
        
        return logCounter;
    }
    
    // Modify data record
    function modifyDataRecord(string memory _dataId, string memory _newName) public onlyAdmin {
        require(dataRecords[_dataId].active, "Data record not found or inactive");
        
        dataRecords[_dataId].dataName = _newName;
        
        emit DataModified(_dataId, msg.sender, block.timestamp);
    }
    
    // Delete data record (soft delete)
    function deleteDataRecord(string memory _dataId) public onlyAdmin {
        require(dataRecords[_dataId].active, "Data record not found or inactive");
        
        dataRecords[_dataId].active = false;
        
        emit DataDeleted(_dataId, msg.sender, block.timestamp);
    }
    
    // Get user's request history
    function getUserRequests(address _userAddress) public view returns (uint256[] memory) {
        return userRequests[_userAddress];
    }
    
    // Get data access logs
    function getDataAccessLogs(string memory _dataId) public view returns (uint256[] memory) {
        return dataAccessLogs[_dataId];
    }
    
    // Get request details
    function getRequestDetails(uint256 _requestId) public view returns (
        address userAddress,
        string memory username,
        string memory dataId,
        string memory dataName,
        uint256 timestamp,
        bool approved,
        bool processed
    ) {
        AccessRequest memory req = accessRequests[_requestId];
        return (
            req.userAddress,
            req.username,
            req.dataId,
            req.dataName,
            req.timestamp,
            req.approved,
            req.processed
        );
    }
    
    // Get total pending requests count
    function getPendingRequestsCount() public view returns (uint256) {
        uint256 count = 0;
        for (uint256 i = 1; i <= requestCounter; i++) {
            if (!accessRequests[i].processed) {
                count++;
            }
        }
        return count;
    }
}
