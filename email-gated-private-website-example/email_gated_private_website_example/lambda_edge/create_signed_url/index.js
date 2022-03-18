const AWS = require('aws-sdk')
const ses = new AWS.SES({ region: 'us-east-1' })
const ssm = new AWS.SSM({ region: 'us-east-1' })

// Either defined as a constant or retrieved from AWS Systems Manager Parameter Store
const SENDER = 'no-reply@mail.weakerpotions.com'

// Either defined as a constant or retrieved from AWS Systems Manager Parameter Store
const SIGNING_URL = 'https://email-gated-private-site-demo.weakerpotions.com'

const signingUrl = `https://${SIGNING_URL}/auth`

const APP_NAME = 'athens-email-gated-demo'
const PRIVATE_KEY_PARAM_NAME = `${APP_NAME}-private-key`
const PUBLIC_KEY_PARAM_NAME = `${APP_NAME}-public-key`

const content = `
<\!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <title>Successful request</title>
  </head>
  <body>
    <p>Email with authentication token sent</p>
  </body>
</html>
`

const response = {
  status: '200',
  statusDescription: 'OK',
  headers: {
    'cache-control': [
      {
        key: 'Cache-Control',
        value: 'max-age=100',
      },
    ],
    'content-type': [
      {
        key: 'Content-Type',
        value: 'text/html',
      },
    ],
  },
  body: content,
}

const error = {
  body: 'Email is not valid',
  bodyEncoding: 'text',
  headers: {
    'content-type': [
      {
        key: 'Content-Type',
        value: 'text/html',
      },
    ],
  },
  status: '204',
  statusDescription: 'Error',
}

const cache = {}

const loadParameter = async (key, withDecryption = false) => {
  const { Parameter } = await ssm
    .getParameter({ Name: key, WithDecryption: withDecryption })
    .promise()
  return Parameter.Value
}

const validateEmail = (allowedDomains, email) => {
  if (!allowedDomains) return false
  const re = /\S+@\S+\.\S+/
  return (
    re.test(email) &&
    allowedDomains.indexOf(email.substring(email.indexOf('@'))) >= 0
  )
}

const sendEmail = async (publicKey, privateKey, email) => {
  const cloudFront = new AWS.CloudFront.Signer(publicKey, privateKey)
  const signedUrl = cloudFront.getSignedUrl({
    url: signingUrl,
    expires: Math.floor(new Date().getTime() / 1000) + 60 * 60 * 1, // Current Time in UTC + time in seconds, (60 * 60 * 1 = 1 hour)
  })

  const params = {
    Destination: {
      ToAddresses: [email],
    },
    Message: {
      Body: {
        Html: {
          Data: signedUrl,
          Charset: 'UTF-8',
        },
      },
      Subject: {
        Data: '[stars on AWS] Login credentials for ' + email,
        Charset: 'UTF-8',
      },
    },
    Source: SENDER,
  }
  await ses.sendEmail(params).promise()
}

exports.handler = async (event, context, callback) => {
  if (cache.allowedDomains == null) {
    cache.allowedDomains = 'gmail.com'
    //cache.allowedDomains = loadParameter('allowedDomains')
  }
    
  if (cache.publicKey == null) {
      cache.publicKey = loadParameter(PUBLIC_KEY_PARAM_NAME)
  }
  if (cache.privateKey == null) {
    //cache.privateKey = loadParameter(PRIVATE_KEY_PARAM_NAME, true)
    cache.privateKey = loadParameter(PRIVATE_KEY_PARAM_NAME)
  }
  const { allowedDomains, publicKey, privateKey } = cache
  const request = event.Records[0].cf.request
  if (request.method === 'GET') {
    const parameters = new URLSearchParams(request.querystring)
    if (parameters.has('email') === false) return error
    const email = parameters.get('email')
    if (!validateEmail(allowedDomains, email)) return error
    else {
      await sendEmail(publicKey, privateKey, email)
      return response
    }
  }
  return error
}
