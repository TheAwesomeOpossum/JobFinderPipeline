---
name: sf-apex-classes
description: "Reference for Salesforce Apex class inventory, categorization by type (batch, schedulable, queueable, REST, service, test, etc.), Tooling API queries, scheduled job introspection, and naming convention detection."
---

# SF Apex Classes — Reference Skill

This skill covers all Apex classes that are NOT trigger-specific (trigger, handler, processor patterns are in `sf-trigger-patterns`). Includes services, utilities, batch jobs, schedulables, queueables, REST/SOAP endpoints, controllers, selectors, test classes, interfaces, invocable actions, and wrappers/DTOs.

---

## 1. Apex Class Categories

Auto-categorization uses naming patterns and known interface/annotation signatures:

| Category | Naming Patterns | Description |
|---|---|---|
| Test Class | `*Test`, `*_Test`, `*Tests` | Unit/integration test classes (`@isTest` annotation) |
| Batch | `*Batch`, `*BatchJob`, implements `Database.Batchable` | Batch Apex for bulk processing of large data volumes |
| Schedulable | `*Schedule`, `*Schedulable`, `*Job`, implements `Schedulable` | Scheduled Apex that runs at defined intervals |
| Queueable | `*Queueable`, `*Queue`, implements `Queueable` | Asynchronous queueable processing with state |
| REST Endpoint | `*RestResource`, `*REST`, `*Api`, `@RestResource` annotation | RESTful web services exposed to external systems |
| SOAP Endpoint | `*WebService`, `webservice` keyword | SOAP web services for external integrations |
| Controller | `*Controller`, `*Ctrl` | Visualforce page or LWC Apex controllers |
| Service | `*Service`, `*Svc` | Business logic service layer classes |
| Selector/DAO | `*Selector`, `*Dao`, `*Repository` | Data access layer for query encapsulation |
| Utility | `*Util`, `*Utils`, `*Helper`, `*Helpers` | Utility and helper classes with reusable methods |
| Interface | `I*`, `*Interface` | Apex interfaces defining contracts |
| Trigger Handler | `*TriggerHandler`, `*Handler` | (cross-ref with `sf-trigger-patterns` skill) |
| Processor | `*Processor` | (cross-ref with `sf-trigger-patterns` skill) |
| Wrapper/DTO | `*Wrapper`, `*DTO`, `*Request`, `*Response` | Data transfer objects and wrapper classes |
| Invocable | `@InvocableMethod`, `@InvocableVariable` | Flow-invocable actions callable from declarative tools |
| Other | _(no pattern match)_ | Uncategorized classes |

**Categorization priority:** When a class matches multiple patterns (e.g., `AccountServiceTest` matches both Service and Test), the highest-priority match wins. Priority order: Test > Batch > Schedulable > Queueable > REST Endpoint > SOAP Endpoint > Controller > Invocable > Service > Selector/DAO > Utility > Interface > Trigger Handler > Processor > Wrapper/DTO > Other.

---

## 2. CLI Commands

### Inventory and Querying

```bash
# List all non-managed Apex classes (full inventory)
sf data query \
  --query "SELECT Id, Name, Status, ApiVersion, LengthWithoutComments, LastModifiedDate, LastModifiedBy.Name FROM ApexClass WHERE NamespacePrefix = null ORDER BY Name" \
  --use-tooling-api --target-org <alias> --json

# Get a single class body (for analysis or categorization)
sf data query \
  --query "SELECT Name, Body FROM ApexClass WHERE Name = '{ClassName}' AND NamespacePrefix = null" \
  --use-tooling-api --target-org <alias>

# List all Apex interfaces
sf data query \
  --query "SELECT Name, ApiVersion, LastModifiedDate FROM ApexClass WHERE NamespacePrefix = null AND Body LIKE '%interface %'" \
  --use-tooling-api --target-org <alias>
```

### Retrieve and Deploy

```bash
# Retrieve a single class (creates .cls + .cls-meta.xml)
sf project retrieve start \
  --metadata "ApexClass:{ClassName}" \
  --target-org <alias>

# Retrieve multiple classes at once
sf project retrieve start \
  --metadata "ApexClass:ClassOne" --metadata "ApexClass:ClassTwo" \
  --target-org <alias>

# Deploy a single class
sf project deploy start \
  --metadata "ApexClass:{ClassName}" \
  --target-org <alias> --wait 10

# Deploy all classes in the project
sf project deploy start \
  --source-dir force-app/main/default/classes \
  --target-org <alias> --wait 10

# Deploy with specific test execution
sf project deploy start \
  --metadata "ApexClass:{ClassName}" \
  --test-level RunSpecifiedTests --tests "{TestClassName}" \
  --target-org <alias> --wait 10
```

### Test Execution

```bash
# Run a specific test class
sf apex run test \
  --class-names "{TestClassName}" \
  --target-org <alias> --wait 10

# Run multiple specific test classes
sf apex run test \
  --class-names "{TestClass1},{TestClass2}" \
  --target-org <alias> --wait 10

# Run a specific test method
sf apex run test \
  --tests "{TestClassName}.{testMethodName}" \
  --target-org <alias> --wait 10

# Run all local tests (excludes managed package tests)
sf apex run test \
  --test-level RunLocalTests \
  --target-org <alias> --wait 10

# Run all tests
sf apex run test \
  --test-level RunAllTestsInOrg \
  --target-org <alias> --wait 10

# Check test results
sf apex get test --test-run-id {testRunId} --target-org <alias>

# Get code coverage for a class
sf apex run test \
  --class-names "{TestClassName}" \
  --code-coverage \
  --target-org <alias> --wait 10
```

### Scheduled and Async Job Introspection

```bash
# Check scheduled Apex jobs (JobType '7' = Scheduled Apex)
sf data query \
  --query "SELECT Id, CronJobDetail.Name, CronJobDetail.JobType, State, NextFireTime, PreviousFireTime, CronExpression FROM CronTrigger WHERE CronJobDetail.JobType = '7' ORDER BY CronJobDetail.Name" \
  --target-org <alias>

# Check currently running/queued async jobs
sf data query \
  --query "SELECT ApexClass.Name, JobType, Status, NumberOfErrors, TotalJobItems, JobItemsProcessed, CreatedDate FROM AsyncApexJob WHERE Status IN ('Holding','Queued','Preparing','Processing') ORDER BY CreatedDate DESC LIMIT 25" \
  --target-org <alias>

# Check recent async job failures
sf data query \
  --query "SELECT ApexClass.Name, JobType, Status, NumberOfErrors, ExtendedStatus, CreatedDate, CompletedDate FROM AsyncApexJob WHERE Status = 'Failed' ORDER BY CreatedDate DESC LIMIT 25" \
  --target-org <alias>

# Abort a scheduled job
sf data query \
  --query "SELECT Id FROM CronTrigger WHERE CronJobDetail.Name = '{JobName}'" \
  --target-org <alias>
# Then: System.abortJob('{CronTriggerId}'); via Execute Anonymous

# Execute anonymous Apex (useful for scheduling/unscheduling)
sf apex run \
  --file script.apex \
  --target-org <alias>
```

---

## 3. Apex Class Metadata XML

**Canonical path:**
```
force-app/main/default/classes/{ClassName}.cls
force-app/main/default/classes/{ClassName}.cls-meta.xml
```

**Meta XML template (same for all class types):**
```xml
<?xml version="1.0" encoding="UTF-8"?>
<ApexClass xmlns="http://soap.sforce.com/2006/04/metadata">
    <apiVersion>66.0</apiVersion>
    <status>Active</status>
</ApexClass>
```

Every `.cls` file requires a corresponding `.cls-meta.xml` file. The meta XML is identical regardless of whether the class is a service, batch, test, interface, or any other type.

---

## 4. Common Apex Patterns

### 4.1 Batch Apex Template

```apex
public class MyObjectBatch implements Database.Batchable<SObject>, Database.Stateful {
    private Integer recordsProcessed = 0;
    private List<String> errors = new List<String>();

    public Database.QueryLocator start(Database.BatchableContext bc) {
        return Database.getQueryLocator([
            SELECT Id, Name, Status__c
            FROM MyObject__c
            WHERE Status__c = 'Pending'
        ]);
    }

    public void execute(Database.BatchableContext bc, List<SObject> scope) {
        List<MyObject__c> records = (List<MyObject__c>) scope;
        List<MyObject__c> toUpdate = new List<MyObject__c>();

        for (MyObject__c rec : records) {
            try {
                rec.Status__c = 'Processed';
                toUpdate.add(rec);
                recordsProcessed++;
            } catch (Exception e) {
                errors.add(rec.Id + ': ' + e.getMessage());
            }
        }

        if (!toUpdate.isEmpty()) {
            Database.SaveResult[] results = Database.update(toUpdate, false);
            for (Integer i = 0; i < results.size(); i++) {
                if (!results[i].isSuccess()) {
                    errors.add(toUpdate[i].Id + ': ' + results[i].getErrors()[0].getMessage());
                }
            }
        }
    }

    public void finish(Database.BatchableContext bc) {
        // Post-processing: send notification, log results
        System.debug('Records processed: ' + recordsProcessed);
        if (!errors.isEmpty()) {
            System.debug('Errors: ' + String.join(errors, '\n'));
        }
    }
}
```

**Key notes:**
- `Database.Stateful` preserves instance variable values between `execute()` calls
- Without `Database.Stateful`, instance variables reset to their initial values each batch
- Default batch size is 200; max is 2,000
- Add `Database.AllowsCallouts` if the batch needs to make HTTP callouts
- Use `Database.update(records, false)` (allOrNone=false) for partial success handling

---

### 4.2 Schedulable Template

```apex
public class MyObjectSchedule implements Schedulable {
    public void execute(SchedulableContext sc) {
        Database.executeBatch(new MyObjectBatch(), 200);
    }
}
```

**Scheduling via Execute Anonymous:**
```apex
// Schedule to run daily at 6 AM
String cronExp = '0 0 6 * * ?';
System.schedule('My Object Daily Processing', cronExp, new MyObjectSchedule());

// Schedule to run every hour
String cronExp = '0 0 * * * ?';
System.schedule('My Object Hourly Sync', cronExp, new MyObjectSchedule());

// Schedule to run every weekday at 8 AM
String cronExp = '0 0 8 ? * MON-FRI';
System.schedule('My Object Weekday Job', cronExp, new MyObjectSchedule());
```

**Cron expression format:** `Seconds Minutes Hours Day_of_month Month Day_of_week [Optional_year]`

| Field | Values |
|---|---|
| Seconds | 0-59 |
| Minutes | 0-59 |
| Hours | 0-23 |
| Day of month | 1-31, `?`, `L`, `W` |
| Month | 1-12 or JAN-DEC |
| Day of week | 1-7 or SUN-SAT, `?`, `L`, `#` |

---

### 4.3 Queueable Template

```apex
public class MyObjectQueueable implements Queueable, Database.AllowsCallouts {
    private List<Id> recordIds;

    public MyObjectQueueable(List<Id> recordIds) {
        this.recordIds = recordIds;
    }

    public void execute(QueueableContext qc) {
        List<MyObject__c> records = [
            SELECT Id, Name, External_Id__c
            FROM MyObject__c
            WHERE Id IN :recordIds
        ];

        // Process records
        for (MyObject__c rec : records) {
            // Business logic here
        }

        // Chain to next job if needed (limit: 1 child job per parent)
        if (!records.isEmpty()) {
            System.enqueueJob(new NextStepQueueable(recordIds));
        }
    }
}

// Enqueue: System.enqueueJob(new MyObjectQueueable(recordIds));
```

**Key notes:**
- Queueable can accept complex types as constructor parameters (unlike `@future`)
- Can chain: one child job per parent (non-test context)
- Add `Database.AllowsCallouts` for HTTP callouts
- Can implement `Finalizer` interface for error handling (Winter '22+)

---

### 4.4 REST Endpoint Template

```apex
@RestResource(urlMapping='/myendpoint/v1/*')
global class MyRestResource {

    @HttpGet
    global static String doGet() {
        RestRequest req = RestContext.request;
        RestResponse res = RestContext.response;
        String recordId = req.requestURI.substring(req.requestURI.lastIndexOf('/') + 1);

        try {
            MyObject__c record = [SELECT Id, Name FROM MyObject__c WHERE Id = :recordId LIMIT 1];
            return JSON.serialize(record);
        } catch (QueryException e) {
            res.statusCode = 404;
            return '{"error": "Record not found"}';
        }
    }

    @HttpPost
    global static String doPost(String name, String status) {
        RestResponse res = RestContext.response;
        try {
            MyObject__c record = new MyObject__c(
                Name = name,
                Status__c = status
            );
            insert record;
            res.statusCode = 201;
            return JSON.serialize(record);
        } catch (DmlException e) {
            res.statusCode = 400;
            return '{"error": "' + e.getMessage() + '"}';
        }
    }

    @HttpPut
    global static String doPut(String id, String name, String status) {
        RestResponse res = RestContext.response;
        try {
            MyObject__c record = [SELECT Id FROM MyObject__c WHERE Id = :id LIMIT 1];
            record.Name = name;
            record.Status__c = status;
            update record;
            return JSON.serialize(record);
        } catch (Exception e) {
            res.statusCode = 400;
            return '{"error": "' + e.getMessage() + '"}';
        }
    }

    @HttpDelete
    global static void doDelete() {
        RestRequest req = RestContext.request;
        RestResponse res = RestContext.response;
        String recordId = req.requestURI.substring(req.requestURI.lastIndexOf('/') + 1);
        try {
            delete [SELECT Id FROM MyObject__c WHERE Id = :recordId LIMIT 1];
            res.statusCode = 204;
        } catch (Exception e) {
            res.statusCode = 400;
        }
    }
}
```

**Key notes:**
- Class and methods must be `global`
- URL mapping: `/services/apexrest/myendpoint/v1/*`
- `@HttpPatch` is also available for partial updates
- Test with `Test.setMock()` is not needed for REST resources; test them by calling the methods directly

---

### 4.5 SOAP Web Service Template

```apex
global class MyWebService {
    webservice static String processRecord(String recordId) {
        try {
            MyObject__c record = [SELECT Id, Name FROM MyObject__c WHERE Id = :recordId LIMIT 1];
            // Process
            return 'Success';
        } catch (Exception e) {
            return 'Error: ' + e.getMessage();
        }
    }

    webservice static List<String> getRecordNames(List<String> recordIds) {
        List<String> names = new List<String>();
        for (MyObject__c rec : [SELECT Name FROM MyObject__c WHERE Id IN :recordIds]) {
            names.add(rec.Name);
        }
        return names;
    }
}
```

**Key notes:**
- Class must be `global`; methods use `webservice` keyword (not an annotation)
- WSDL auto-generated at Setup > Apex Classes > Generate WSDL
- Cannot use `webservice` with `@RestResource` in the same class

---

### 4.6 Invocable Method Template (Flow Integration)

```apex
public class MyInvocableAction {

    @InvocableMethod(
        label='My Action Label'
        description='Performs a specific business operation'
        category='Custom'
    )
    public static List<Result> execute(List<Request> requests) {
        List<Result> results = new List<Result>();

        // Collect IDs for bulk query
        Set<Id> recordIds = new Set<Id>();
        for (Request req : requests) {
            recordIds.add(req.recordId);
        }

        // Query once
        Map<Id, MyObject__c> recordMap = new Map<Id, MyObject__c>(
            [SELECT Id, Name, Status__c FROM MyObject__c WHERE Id IN :recordIds]
        );

        // Process
        for (Request req : requests) {
            Result res = new Result();
            MyObject__c record = recordMap.get(req.recordId);
            if (record != null) {
                res.success = true;
                res.outputMessage = 'Processed: ' + record.Name;
            } else {
                res.success = false;
                res.outputMessage = 'Record not found';
            }
            results.add(res);
        }

        return results;
    }

    public class Request {
        @InvocableVariable(label='Record Id' description='The record to process' required=true)
        public Id recordId;

        @InvocableVariable(label='Action Type' description='Type of action to perform' required=false)
        public String actionType;
    }

    public class Result {
        @InvocableVariable(label='Success' description='Whether the action succeeded')
        public Boolean success;

        @InvocableVariable(label='Output Message' description='Result message')
        public String outputMessage;
    }
}
```

**Key notes:**
- Only one `@InvocableMethod` per class
- Input/output must be `List<>` (Flow handles bulkification)
- Inner classes with `@InvocableVariable` appear as inputs/outputs in Flow Builder
- Supported types: `String`, `Boolean`, `Integer`, `Decimal`, `Date`, `DateTime`, `Id`, `SObject`, and collections thereof

---

### 4.7 Service Layer Template

```apex
public with sharing class AccountService {

    public static void updateAccountStatuses(Set<Id> accountIds, String newStatus) {
        List<Account> accounts = [
            SELECT Id, Status__c
            FROM Account
            WHERE Id IN :accountIds
        ];

        for (Account acct : accounts) {
            acct.Status__c = newStatus;
        }

        if (!accounts.isEmpty()) {
            update accounts;
        }
    }

    public static Map<Id, Integer> getContactCounts(Set<Id> accountIds) {
        Map<Id, Integer> countMap = new Map<Id, Integer>();
        for (AggregateResult ar : [
            SELECT AccountId, COUNT(Id) cnt
            FROM Contact
            WHERE AccountId IN :accountIds
            GROUP BY AccountId
        ]) {
            countMap.put((Id) ar.get('AccountId'), (Integer) ar.get('cnt'));
        }
        return countMap;
    }
}
```

**Key notes:**
- Service classes encapsulate business logic, callable from triggers, controllers, batch, etc.
- Use `with sharing` by default (enforces record-level security)
- Methods should be `public static` for stateless operations
- Accept bulk parameters (`Set<Id>`, `List<SObject>`) to support bulkification

---

### 4.8 Selector / DAO Template

```apex
public with sharing class AccountSelector {

    public static List<Account> getByIds(Set<Id> accountIds) {
        return [
            SELECT Id, Name, Industry, BillingCity, BillingState
            FROM Account
            WHERE Id IN :accountIds
        ];
    }

    public static List<Account> getByIndustry(String industry) {
        return [
            SELECT Id, Name, Industry, AnnualRevenue
            FROM Account
            WHERE Industry = :industry
            ORDER BY Name
        ];
    }

    public static List<Account> getWithContacts(Set<Id> accountIds) {
        return [
            SELECT Id, Name,
                (SELECT Id, FirstName, LastName, Email FROM Contacts ORDER BY LastName)
            FROM Account
            WHERE Id IN :accountIds
        ];
    }
}
```

**Key notes:**
- Centralizes all SOQL for an object in one class
- Makes queries testable, reusable, and easy to maintain
- Always use `with sharing` unless there is a documented reason not to
- Encapsulate field lists so adding a field only requires one change

---

### 4.9 Utility / Helper Template

```apex
public class StringUtils {

    public static String truncate(String input, Integer maxLength) {
        if (String.isBlank(input)) return input;
        return input.length() > maxLength ? input.substring(0, maxLength) : input;
    }

    public static String formatPhoneNumber(String phone) {
        if (String.isBlank(phone)) return phone;
        String digits = phone.replaceAll('[^0-9]', '');
        if (digits.length() == 10) {
            return '(' + digits.substring(0, 3) + ') ' + digits.substring(3, 6) + '-' + digits.substring(6);
        }
        return phone;
    }

    public static Boolean isValidEmail(String email) {
        if (String.isBlank(email)) return false;
        String emailRegex = '^[a-zA-Z0-9._|\\\\%#~`=?&/$^*!}{+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,4}$';
        Pattern p = Pattern.compile(emailRegex);
        Matcher m = p.matcher(email);
        return m.matches();
    }
}
```

---

### 4.10 Wrapper / DTO Template

```apex
public class AccountWrapper {
    @AuraEnabled public String accountId { get; set; }
    @AuraEnabled public String accountName { get; set; }
    @AuraEnabled public Integer contactCount { get; set; }
    @AuraEnabled public List<ContactInfo> contacts { get; set; }

    public AccountWrapper(Account acct, List<Contact> contacts) {
        this.accountId = acct.Id;
        this.accountName = acct.Name;
        this.contactCount = contacts.size();
        this.contacts = new List<ContactInfo>();
        for (Contact c : contacts) {
            this.contacts.add(new ContactInfo(c));
        }
    }

    public class ContactInfo {
        @AuraEnabled public String name { get; set; }
        @AuraEnabled public String email { get; set; }

        public ContactInfo(Contact c) {
            this.name = c.FirstName + ' ' + c.LastName;
            this.email = c.Email;
        }
    }
}
```

**Key notes:**
- Use `@AuraEnabled` properties when the wrapper is returned to LWC/Aura
- Inner classes keep related DTOs grouped
- Constructors that accept SObjects keep mapping logic centralized

---

### 4.11 Controller Template (LWC Apex)

```apex
public with sharing class MyComponentController {

    @AuraEnabled(cacheable=true)
    public static List<Account> getAccounts(String searchTerm) {
        String likeSearch = '%' + String.escapeSingleQuotes(searchTerm) + '%';
        return [
            SELECT Id, Name, Industry, AnnualRevenue
            FROM Account
            WHERE Name LIKE :likeSearch
            ORDER BY Name
            LIMIT 50
        ];
    }

    @AuraEnabled
    public static Id createRecord(String name, String industry) {
        Account acct = new Account(
            Name = name,
            Industry = industry
        );
        insert acct;
        return acct.Id;
    }

    @AuraEnabled
    public static void updateRecord(Id accountId, String industry) {
        Account acct = [SELECT Id FROM Account WHERE Id = :accountId LIMIT 1];
        acct.Industry = industry;
        update acct;
    }
}
```

**Key notes:**
- `@AuraEnabled(cacheable=true)` for read-only methods (improves LWC performance)
- `cacheable=true` methods cannot perform DML
- Always use `String.escapeSingleQuotes()` for user-supplied search terms
- Use `with sharing` to enforce record-level security in the UI context

---

## 5. Apex Governor Limits Quick Reference

| Limit | Synchronous | Asynchronous |
|---|---|---|
| SOQL queries | 100 | 200 |
| SOQL rows retrieved | 50,000 | 50,000 |
| DML statements | 150 | 150 |
| DML rows | 10,000 | 10,000 |
| Callouts | 100 | 100 |
| CPU time | 10,000 ms | 60,000 ms |
| Heap size | 6 MB | 12 MB |
| Future calls | 50 | 0 (cannot call @future from async) |
| Queueable jobs (enqueue) | 50 | 1 |
| Email invocations | 10 | 10 |
| SOSL queries | 20 | 20 |
| Describe calls | 100 | 100 |

### Batch Apex Specific Limits

| Limit | Value |
|---|---|
| Default batch size | 200 |
| Maximum batch size | 2,000 |
| Concurrent batches | 5 (active) |
| Queued batches | 100 |
| `start()` query locator rows | 50 million |
| `execute()` governor limits | Per-batch (reset each execute call) |

### Org-Wide Limits

| Limit | Value |
|---|---|
| Scheduled Apex jobs | 100 |
| Apex classes in org | 6,000 (varies by edition) |
| Code size per class | 1 million characters |
| Total Apex code size | 6 MB (varies by edition) |

---

## 6. Async Apex Decision Guide

| Method | Use When | State | Callouts | Chaining | Limits |
|---|---|---|---|---|---|
| `@future` | Simple fire-and-forget, callout needed | No state (primitives only) | Yes (with `callout=true`) | No chaining | 50 per transaction |
| `Queueable` | Complex async, needs object params | Full state (any type) | Yes (with `AllowsCallouts`) | 1 child per parent | 50 enqueued per transaction |
| `Batch` | Process large data volumes (millions) | Optional (`Database.Stateful`) | Yes (with `AllowsCallouts`) | Via `finish()` | 5 concurrent, 100 queued |
| `Schedulable` | Run at specific times/intervals | Full state | No (schedule batch/queueable instead) | Invoke batch/queueable | 100 scheduled jobs max |

### When to use what:

- **Need a callout from a trigger?** Use `@future(callout=true)` for simple cases, `Queueable` for complex
- **Processing >50k records?** Use Batch
- **Need to chain multiple async steps?** Use Queueable (chain 1) or Batch (chain in finish())
- **Need to run on a schedule?** Schedulable that invokes Batch or Queueable
- **Need to pass complex objects?** Queueable (future only accepts primitives)

---

## 7. Test Class Patterns

### 7.1 Core Test Structure

```apex
@isTest
private class MyServiceTest {

    @TestSetup
    static void setupTestData() {
        // Create shared test data used across multiple test methods
        Account testAccount = new Account(Name = 'Test Account');
        insert testAccount;

        List<Contact> contacts = new List<Contact>();
        for (Integer i = 0; i < 5; i++) {
            contacts.add(new Contact(
                FirstName = 'Test',
                LastName = 'Contact ' + i,
                AccountId = testAccount.Id
            ));
        }
        insert contacts;
    }

    @isTest
    static void testMethodName_positiveScenario() {
        // Arrange
        Account acct = [SELECT Id FROM Account LIMIT 1];

        // Act
        Test.startTest();
        String result = MyService.processAccount(acct.Id);
        Test.stopTest();

        // Assert
        System.assertEquals('Success', result, 'Should return success for valid account');
    }

    @isTest
    static void testMethodName_negativeScenario() {
        // Arrange — use invalid data

        // Act
        Test.startTest();
        try {
            MyService.processAccount(null);
            System.assert(false, 'Should have thrown exception');
        } catch (MyService.MyException e) {
            // Assert
            System.assert(e.getMessage().contains('required'), 'Exception message should mention required field');
        }
        Test.stopTest();
    }

    @isTest
    static void testMethodName_bulkScenario() {
        // Test with 200 records to verify bulkification
        List<Account> accounts = new List<Account>();
        for (Integer i = 0; i < 200; i++) {
            accounts.add(new Account(Name = 'Bulk Test ' + i));
        }
        insert accounts;

        Test.startTest();
        MyService.processAccounts(new Map<Id, Account>(accounts).keySet());
        Test.stopTest();

        // Assert expected outcomes
    }
}
```

### 7.2 Testing Async Apex

```apex
// Testing Batch
@isTest
static void testBatch() {
    // Create test data
    Test.startTest();
    Database.executeBatch(new MyObjectBatch(), 200);
    Test.stopTest();
    // Assertions here — batch runs synchronously in test context
}

// Testing Queueable
@isTest
static void testQueueable() {
    Test.startTest();
    System.enqueueJob(new MyObjectQueueable(recordIds));
    Test.stopTest();
    // Assertions here — queueable runs synchronously in test context
}

// Testing Schedulable
@isTest
static void testSchedulable() {
    Test.startTest();
    String cronExp = '0 0 6 * * ?';
    String jobId = System.schedule('Test Job', cronExp, new MyObjectSchedule());
    Test.stopTest();

    CronTrigger ct = [SELECT Id, TimesTriggered FROM CronTrigger WHERE Id = :jobId];
    System.assertNotEquals(null, ct, 'Job should be scheduled');
}

// Testing Future
@isTest
static void testFutureMethod() {
    Test.startTest();
    MyService.myFutureMethod(recordId);
    Test.stopTest();
    // Assertions here — future runs synchronously between startTest/stopTest
}
```

### 7.3 Testing REST Endpoints

```apex
@isTest
static void testRestGet() {
    Account testAccount = new Account(Name = 'REST Test');
    insert testAccount;

    RestRequest req = new RestRequest();
    req.requestURI = '/services/apexrest/myendpoint/v1/' + testAccount.Id;
    req.httpMethod = 'GET';
    RestContext.request = req;
    RestContext.response = new RestResponse();

    Test.startTest();
    String result = MyRestResource.doGet();
    Test.stopTest();

    System.assert(result.contains('REST Test'), 'Should return account name');
}
```

### 7.4 HTTP Callout Mocking

```apex
// Mock class
@isTest
public class MyHttpMock implements HttpCalloutMock {
    public HTTPResponse respond(HTTPRequest req) {
        HttpResponse res = new HttpResponse();
        res.setStatusCode(200);
        res.setBody('{"status":"success","id":"ext-123"}');
        res.setHeader('Content-Type', 'application/json');
        return res;
    }
}

// In test method
@isTest
static void testCallout() {
    Test.setMock(HttpCalloutMock.class, new MyHttpMock());

    Test.startTest();
    String result = MyService.makeCallout();
    Test.stopTest();

    System.assertEquals('success', result, 'Callout should return success');
}
```

### 7.5 Test Best Practices

| Practice | Detail |
|---|---|
| `@TestSetup` | Use for shared data across test methods; re-inserted per method |
| `Test.startTest()` / `Test.stopTest()` | Resets governor limits; executes async synchronously |
| `System.runAs()` | Test with specific user context / profile / permission set |
| `System.assertEquals(expected, actual, message)` | Always include descriptive message (3rd param) |
| Avoid `SeeAllData=true` | Creates dependency on org data; use `@TestSetup` instead |
| 75% coverage | Minimum for deployment; aim for meaningful assertions, not just coverage |
| Test both positive and negative | Include error cases, null inputs, boundary conditions |
| Bulk test (200 records) | Verify no SOQL/DML in loops |

---

## 8. Sharing and Security Keywords

| Keyword | Behavior |
|---|---|
| `with sharing` | Enforces record-level security (sharing rules, org-wide defaults) |
| `without sharing` | Ignores sharing rules — system-level access |
| `inherited sharing` | Inherits sharing mode from calling class; uses `with sharing` if called at top level |
| _(no keyword)_ | Behaves as `without sharing` (legacy default — avoid this) |

**Best practice:** Always explicitly declare `with sharing` or `without sharing`. Use `with sharing` by default. Use `without sharing` only when system-level access is deliberately needed (e.g., a service that aggregates data across all records). Use `inherited sharing` for utility classes that should respect whatever context calls them.

---

## 9. Gotchas and Common Issues

| Issue | Detail |
|---|---|
| `LengthWithoutComments` | Tooling API field giving rough complexity/size indicator (character count minus comments) |
| `@isTest` classes | NOT counted toward org code size limits or code coverage requirements |
| `Database.Stateful` | Required to persist instance variables between batch `execute()` calls; without it, variables reset each batch |
| `@future` cannot call `@future` | Future methods cannot invoke other future methods; use Queueable instead for chaining |
| Queueable chaining limit | 1 child job per parent in non-test context; in test context, chaining is not allowed |
| Scheduled job limit | 100 scheduled jobs per org — includes inactive jobs; abort unused jobs to free slots |
| Mixed DML | Cannot perform DML on setup objects (User, PermissionSet) and non-setup objects in the same transaction; use `@future` or `System.runAs()` to separate |
| `Limits.getLimitQueries()` | Returns the limit (100/200), not usage; use `Limits.getQueries()` for current count |
| `System.debug` limits | Debug logs truncate at 5 MB; excessive debug statements in loops can hide useful output |
| Custom exception classes | Must extend `Exception` and conventionally end with `Exception` suffix |
| Deployment order | Deploy interfaces before classes that implement them; deploy parent classes before inner class references |
| `global` vs `public` | `global` is required for managed packages, REST resources, and SOAP web services; use `public` everywhere else |
| Compile-all on deploy | Deploying a class recompiles all dependent classes; a broken dependency can fail your deploy even if the class you are deploying is correct |

---

## 10. Apex Access Modifiers Reference

| Modifier | Visibility |
|---|---|
| `private` | Same class only (default for inner classes) |
| `public` | Same namespace (your org) |
| `global` | All namespaces (managed packages, REST/SOAP endpoints) |
| `protected` | Same class and subclasses |
| `virtual` | Class/method can be extended/overridden |
| `abstract` | Class cannot be instantiated; must be extended |
| `override` | Method overrides a virtual/abstract parent method |

---

## 11. Common Deploy Errors

| Error | Cause | Fix |
|---|---|---|
| `Dependent class is invalid and needs recompilation` | A dependency was modified or is broken | Deploy the dependency first, then redeploy |
| `Test coverage of selected Apex Classes is 0%, at least 75% required` | No test class covers the target class | Write test class or include existing test in deploy |
| `System.LimitException: Too many SOQL queries: 101` | SOQL in a loop | Bulkify: collect IDs, query once outside loop |
| `System.LimitException: Too many DML statements: 151` | DML in a loop | Collect records, single DML outside loop |
| `System.CalloutException: Callout from scheduled Apex` | Schedulable cannot make callouts directly | Have Schedulable invoke a Queueable or Batch that allows callouts |
| `System.AsyncException: Maximum stack depth has been reached` | Recursive queueable chaining | Add exit condition; limit chain depth |
| `Compile Error: Non-void method might not return a value` | Missing return in all code paths | Add return statement to all branches (including catch) |
| `Method does not exist or incorrect signature` | Wrong parameter types or count | Check method signature matches the call exactly |
| `Variable does not exist` | Field not queried or typo in API name | Add field to SOQL query; check API name spelling |
| `MIXED_DML_OPERATION` | Setup and non-setup DML in same transaction | Separate with `@future` or `System.runAs()` in tests |
| `Class has already been scheduled` | Trying to schedule same class twice with same name | Use unique job name or abort existing job first |
| `too many queueable jobs added to the queue` | Exceeded 50 enqueued jobs in a single transaction | Consolidate work into fewer jobs |

---

## Context Specification

- metadata_type: ApexClass
- context_path: {alias}/apex-classes/
- inventory_file: {alias}/apex-classes/_inventory.md
- detail_file_pattern: _(inventory only)_

### Full Inventory Query
Uses: tooling API
```sql
SELECT Id, Name, Status, ApiVersion, LengthWithoutComments, LastModifiedDate, LastModifiedBy.Name
FROM ApexClass
WHERE NamespacePrefix = null
ORDER BY Name
```

### Supplemental Query: Scheduled Jobs
Uses: standard API
```sql
SELECT Id, CronJobDetail.Name, CronJobDetail.JobType, State, NextFireTime, PreviousFireTime, CronExpression
FROM CronTrigger
WHERE CronJobDetail.JobType = '7'
ORDER BY CronJobDetail.Name
```

### Supplemental Query: Running Async Jobs
Uses: standard API
```sql
SELECT ApexClass.Name, JobType, Status, NumberOfErrors, TotalJobItems, JobItemsProcessed
FROM AsyncApexJob
WHERE Status IN ('Holding','Queued','Preparing','Processing')
ORDER BY CreatedDate DESC
LIMIT 25
```

### Change Detection Query
Uses: tooling API
```sql
SELECT Name, Status, ApiVersion, LengthWithoutComments, LastModifiedDate, LastModifiedBy.Name
FROM ApexClass
WHERE NamespacePrefix = null
AND LastModifiedDate > {LAST_SCAN}
ORDER BY LastModifiedDate DESC
LIMIT 50
```

### Inventory Columns
Class Name | Category | Status | API Version | Size (chars) | Last Modified Date | Last Modified By

### Detail File Sections
_(No per-class detail files -- inventory with auto-categorization is sufficient. Retrieve individual class with `sf project retrieve start --metadata "ApexClass:{Name}"`)_

### Naming Convention Detection
Analyze all ApexClass names and extract:
- **Casing style:** PascalCase vs mixed
- **Class structure pattern:** `{Object}{Role}` (e.g., AccountService) vs `{Role}{Object}` vs other
- **Test class suffix:** `Test` vs `_Test` vs `Tests`
- **Interface prefix/suffix:** `I{Name}` vs `{Name}Interface`
- **Batch/Schedule suffix:** `Batch` vs `BatchJob` vs `BatchProcess`
- **Service layer naming:** `Service` vs `Svc` vs `Manager`
- Report findings in `## Detected Naming Conventions` at the top of `_inventory.md`
