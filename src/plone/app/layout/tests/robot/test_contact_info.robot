*** Settings ***

Resource    plone/app/robotframework/browser.robot
Resource    Products/CMFPlone/tests/robot/keywords.robot

Library    Remote    ${PLONE_URL}/RobotRemote

Test Setup    Run Keywords    Plone test setup
Test Teardown    Run keywords     Plone test teardown


*** Test Cases ***

Scenario: Contact form overlay opens
    Given the site root
     When I click the 'Contact' link
     Then overlay should open

Scenario: Contact form overlay closes
    Given the site root logged out
      and the 'Contact' overlay
     When I close the overlay
     Then overlay should close


*** Keywords ***

# GIVEN

the site root logged out
    Go to    ${PLONE_URL}/logout

the site root
    Go to    ${PLONE_URL}

the '${link_name}' overlay
    Click    //a[descendant-or-self::*[contains(text(), "${link_name}")]]
    Get Element Count    //div[contains(@class,"modal-dialog")]    greater than    0

# WHEN

I click the '${link_name}' link
    Get Element Count    //a[descendant-or-self::*[contains(text(), "${link_name}")]]    greater than    0
    Click    //a[descendant-or-self::*[contains(text(), "${link_name}")]]

I close the overlay
    Click    //div[contains(@class,"modal-header")]//button[contains(@class,"modal-close")]

# THEN

overlay should open
    Wait For Condition    Element States    //div[contains(@class,"modal-dialog")]    contains    visible

overlay should close
    Wait For Condition    Element Count    //div[contains(@class,"modal-dialog")]    should be    0
