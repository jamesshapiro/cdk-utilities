const AWS = require('aws-sdk');
const ssm = new AWS.SSM({ region: 'us-east-1' });

// Either defined as a constant or retrieved from AWS Systems Manager Parameter Store
const SIGNING_URL = 'email-gated-private-site-demo.weakerpotions.com'

const APP_NAME = 'athens-email-gated-demo'
const PRIVATE_KEY_PARAM_NAME = `${APP_NAME}-private-key`
const PUBLIC_KEY_PARAM_NAME = `${APP_NAME}-public-key-id`

const cache = {}

const loadParameter = async(key, WithDecryption = false) => {
    console.log("Loading Parameter...")
    const { Parameter } = await ssm.getParameter({ Name: key, WithDecryption: WithDecryption }).promise();
    console.log(`Parameter loaded with value ${Parameter.value}`)
    return Parameter.Value;
};

const policyString = JSON.stringify({
    'Statement': [{
        'Resource': `http*://${SIGNING_URL}/*`,
        'Condition': {
            'DateLessThan': { 'AWS:EpochTime': getExpiryTime() }
        }
    }]
});

function getSignedCookie(publicKey, privateKey) {
    const cloudFront = new AWS.CloudFront.Signer(publicKey, privateKey);
    const options = { policy: policyString };
    return cloudFront.getSignedCookie(options);
}

function getExpirationTime() {
    const date = new Date();
    return new Date(date.getFullYear(), date.getMonth() + 1, 0, 23, 59, 59);
}

function getExpiryTime() {
    return Math.floor(getExpirationTime().getTime() / 1000);
}

exports.handler = async(event) => {
    console.log(cache)
    if (cache.publicKey == null) cache.publicKey = await loadParameter(PUBLIC_KEY_PARAM_NAME)
    //if (cache.privateKey == null) cache.privateKey = loadParameter('privateKey', true);
    if (cache.privateKey == null)
      cache.privateKey = await loadParameter(PRIVATE_KEY_PARAM_NAME)

    const { publicKey, privateKey } = cache;
    console.log(`public key = ${publicKey}`)
    console.log(`private key = ${privateKey}`)

    const signedCookie = getSignedCookie(publicKey, privateKey);

    return {
        status: '302',
        statusDescription: 'Found',
        headers: {
            location: [{
                key: 'Location',
                value: `https://${SIGNING_URL}/restricted-content.html`,
            }],
            'cache-control': [{
                key: "Cache-Control",
                value: "no-cache, no-store, must-revalidate"
            }],
            'set-cookie': [{
                key: "Set-Cookie",
                value: `CloudFront-Policy=${signedCookie['CloudFront-Policy']};Domain=${SIGNING_URL};Path=/;Expires=${getExpirationTime().toUTCString()};Secure;HttpOnly;SameSite=Lax`
            }, {
                key: "Set-Cookie",
                value: `CloudFront-Key-Pair-Id=${signedCookie['CloudFront-Key-Pair-Id']};Domain=${SIGNING_URL};Path=/;Expires=${getExpirationTime().toUTCString()};Secure;HttpOnly;SameSite=Lax`
            }, {
                key: "Set-Cookie",
                value: `CloudFront-Signature=${signedCookie['CloudFront-Signature']};Domain=${SIGNING_URL};Path=/;Expires=${getExpirationTime().toUTCString()};Secure;HttpOnly;SameSite=Lax`
            }]
        },
    };
};